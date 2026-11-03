"""Normalize free disc phases, then solve the finite Pentacle colour group."""
from functools import lru_cache
from collections import Counter
import math
import hashlib
import json
from pathlib import Path
from time import monotonic
import zlib
from cube.pentacle import PentacleCube
from cube.polyhedral import CUBE,dot,cross,Move
from cube.articulated_observation import polygon_key


def panel_key(patches):return tuple(sorted(polygon_key(poly) for poly in patches))


@lru_cache(maxsize=1)
def root_slots():
    cube=PentacleCube();world=cube.world_panels()
    slots={panel_key(patches):i for i,patches in enumerate(world)}
    if len(slots)!=len(world):raise ValueError('pentacle.invalid_geometry')
    centres=[]
    for face,normal in enumerate(CUBE):
        candidates=[]
        for i,panel in enumerate(cube.panels):
            if panel.face!=face or panel.home not in cube.discs:continue
            poly=world[i][0];point=tuple(sum(p[a] for p in poly)/len(poly)-normal[a] for a in range(3))
            candidates.append((dot(point,point),i))
        centres.append(min(candidates)[1])
    return cube,slots,tuple(centres)


def disc_corrections(cube):
    root,slots,centres=root_slots();world=cube.world_panels();base=root.world_panels();result=[]
    for face,index in enumerate(centres):
        normal=CUBE[face];a=world[index][0][0];b=base[index][0][0]
        source=tuple(a[i]-normal[i] for i in range(3));target=tuple(b[i]-normal[i] for i in range(3))
        angle=math.degrees(math.atan2(dot(cross(source,target),normal),dot(source,target)))
        # A pentagon has five indistinguishable geometric orientations. Use
        # the shortest correction; the remaining 72-degree steps belong to
        # the finite colour permutation group.
        angle=round((angle+36.)%72.-36.,10)
        result.append(angle)
    return tuple(result)


def normalize(cube,cancel=None):
    work=cube.clone();work.history=[];word=[]
    for face,angle in enumerate(disc_corrections(work)):
        if cancel and cancel():raise InterruptedError()
        if abs(angle)<1e-6:continue
        move=Move(face,0,angle);work.apply_move(move);word.append(move)
    slots=root_slots()[1]
    if {panel_key(patches) for patches in work.world_panels()}!=set(slots):
        raise ValueError('pentacle.invalid_geometry')
    return work,tuple(word)


def permutation(cube):
    slots=root_slots()[1]
    return tuple(slots.get(panel_key(patches),-1) for patches in cube.world_panels())


@lru_cache(maxsize=1)
def geometry_fingerprint():
    from cube.pentacle import RADIUS,CUT
    cube=root_slots()[0]
    def stable(value):
        if isinstance(value,float):return round(value,8) or 0.
        if isinstance(value,(tuple,list)):return tuple(stable(v) for v in value)
        return value
    raw=stable((CUBE,RADIUS,CUT,72,90,tuple((p.home,p.face,p.patches) for p in cube.panels)))
    return hashlib.sha256(json.dumps(raw,separators=(',',':')).encode()).hexdigest()


@lru_cache(maxsize=1)
def table():
    try:data=json.loads(zlib.decompress((Path(__file__).parent/'data/pentacle_group.bin').read_bytes()))
    except (OSError,ValueError,zlib.error):raise ValueError('pentacle.solver_data') from None
    if data.get('version')!=1 or data.get('kind')!='pentacle' or data.get('geometry')!=geometry_fingerprint():raise ValueError('pentacle.solver_data')
    return data


def solve_pentacle_state(cube,cancel=None,progress=None,*,seconds=None):
    if cancel and cancel():raise InterruptedError()
    work,prefix=normalize(cube,cancel);data=table()
    # The resource describes mechanical permutations, including hidden
    # carriers. Their positions/colours are not part of the visible goal.
    hidden=work.hidden_panels
    wanted=tuple(-2 if i in hidden else c for i,c in enumerate(data['goal_colors']))
    state=[-1]*len(wanted)
    for i,dest in enumerate(permutation(work)):
        if dest<0:raise ValueError('pentacle.invalid_geometry')
        state[dest]=work._paints[i]
    if any(type(c) is not int or (c!=-2 if i in hidden else c not in range(6))
           for i,c in enumerate(state)):raise ValueError('pentacle.invalid_colours')
    for orbit in data['orbits']:
        if Counter(state[i] for i in orbit)!=Counter(wanted[i] for i in orbit):raise ValueError('pentacle.invalid_colours')
    begun=monotonic();nodes=0;seen=set()
    def visit(level,current):
        nonlocal nodes
        if cancel and cancel():raise InterruptedError()
        nodes+=1
        if seconds is not None and monotonic()-begun>seconds:raise ValueError('rigid.search_limit')
        if current==wanted:return ()
        if level==len(data['base']) or (level,current) in seen:return None
        if len(seen)<12000:seen.add((level,current))
        point=data['base'][level];following=[]
        for beta,entry in data['transversals'][level].items():
            if current[int(beta)]!=wanted[point]:continue
            child=tuple(current[i] for i in entry['permutation'])
            following.append((sum(a!=b for a,b in zip(child,wanted)),len(entry['word']),int(beta),child,entry))
        for _,_,beta,child,entry in sorted(following):
            tail=visit(level+1,child)
            if tail is not None:return (entry,)+tail
        return None
    factors=visit(0,tuple(state))
    if factors is None:raise ValueError('pentacle.state_unreachable')
    word=prefix+tuple(Move(a,l,-n) for entry in factors for a,l,n in reversed(entry['word']))
    replay=cube.clone()
    for i,move in enumerate(word):
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
        if progress and i%20==0:progress(i,len(word))
    if not replay.is_solved():raise ValueError('pentacle.replay_failed')
    if progress:progress(len(word),len(word))
    return word
