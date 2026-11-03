"""Two coupled corner-orientation systems of the 4x4x2 brick mechanism."""
from collections import deque
from functools import lru_cache
from itertools import product
from cube.cuboid import layout,turn_frame,transform
from cube.polyhedral import CUBE,Move
import hashlib
import json
from pathlib import Path
from time import monotonic
import struct
import zlib

OCTANTS=tuple(product((-1,1),repeat=3))
AT={p:i for i,p in enumerate(OCTANTS)}
MOVES=tuple(Move(f,l,n) for f in range(6) for l in range(3) for n in (1,2,3))


@lru_cache(maxsize=1)
def geometry_fingerprint():
    from cube.appearance import ROTATIONS
    cells,boxes,entries,*_=layout('cuboid_442')
    raw=(cells,boxes,entries,ROTATIONS,tuple((m.axis,m.layer,m.amount) for m in MOVES))
    return hashlib.sha256(json.dumps(raw,separators=(',',':')).encode()).hexdigest()


@lru_cache(maxsize=1)
def corner_actions():
    result={}
    for face in range(6):
        axis=next(a for a,v in enumerate(CUBE[face]) if v);sign=CUBE[face][axis]
        for amount in (1,2,3):
            frame=turn_frame(face,amount)
            positions=tuple(AT[transform(frame,p)] for p in OCTANTS)
            axes=tuple(next(a for a,v in enumerate(transform(frame,tuple(int(j==i) for j in range(3)))) if v) for i in range(3))
            selected=tuple(i for i,p in enumerate(OCTANTS) if p[axis]==sign)
            result[face,amount]=positions,axes,selected,axis
    return result


def corner_turn(state,face,amount,whole=False):
    positions,axes,selected,axis=corner_actions()[face,amount];out=list(state)
    for i in (range(8) if whole else selected):out[positions[i]]=axes[state[i]]
    return tuple(out)


def transition(outer,inner,move):
    positions,axes,selected,axis=corner_actions()[move.axis,move.amount]
    if move.layer!=1:
        face=move.axis if move.layer==0 else (move.axis+3)%6
        cut=corner_actions()[face,move.amount][2]
        if any(outer[i]==axis or inner[i]==axis for i in cut):return None
    following_outer=corner_turn(outer,move.axis,move.amount)
    following_inner=(inner if move.layer==0 else corner_turn(inner,move.axis,move.amount,whole=move.layer==2))
    return following_outer,following_inner


def code(values):return sum(v*3**i for i,v in enumerate(values))


@lru_cache(maxsize=1)
def corner_states():
    root=(1,)*8;states=[root];index={code(root):0};pending=deque([root])
    while pending:
        state=pending.popleft()
        for face in range(6):
            for n in (1,2,3):
                child=corner_turn(state,face,n);key=code(child)
                if key not in index:index[key]=len(states);states.append(child);pending.append(child)
    assert len(states)==2187
    return tuple(states),index


@lru_cache(maxsize=1)
def tracked_bricks():
    groups=layout('cuboid_442')[0];outer=[];inner=[]
    for piece,group in enumerate(groups):
        for p in group:
            if all(abs(v)==3 for v in p):outer.append((piece,p))
            if all(abs(v)==1 for v in p):inner.append((piece,p))
    assert len(outer)==len(inner)==8
    return tuple(outer),tuple(inner)


def orientations(cube):
    result=[]
    for pieces in tracked_bricks():
        values=[None]*8
        for piece,point in pieces:
            frame=cube.frames[piece];position=transform(frame,point)
            slot=AT[tuple(1 if v>0 else -1 for v in position)]
            normal=transform(frame,(0,1,0));values[slot]=next(a for a,v in enumerate(normal) if v)
        if any(v is None for v in values):raise ValueError('cuboid.identity_conflict')
        result.append(tuple(values))
    return tuple(result)


@lru_cache(maxsize=1)
def solver_data():
    folder=Path(__file__).parent/'data'
    try:
        raw=(folder/'cuboid_442_orientations.bin').read_bytes()
        size=struct.unpack_from('<I',raw,4)[0];header=json.loads(raw[8:8+size]);parents=zlib.decompress(raw[8+size:])
        group=json.loads(zlib.decompress((folder/'cuboid_442_group.bin').read_bytes()))
    except (OSError,ValueError,struct.error,zlib.error):raise ValueError('cuboid.solver_data') from None
    fingerprint=geometry_fingerprint()
    if (raw[:4]!=b'CO01' or header.get('version')!=1 or header.get('geometry')!=fingerprint
        or group.get('version')!=1 or group.get('kind')!='cuboid_442' or group.get('geometry')!=fingerprint
        or len(parents)!=2187**2 or header.get('corner_count')!=2187):raise ValueError('cuboid.solver_data')
    indices={code(state):i for i,state in enumerate(header['states'])}
    if len(indices)!=2187:raise ValueError('cuboid.solver_data')
    return header,parents,group,indices


def solve_cuboid442(cube,cancel=None,progress=None,*,seconds=None):
    if cancel and cancel():raise InterruptedError()
    if cube.is_solved():return ()
    from solver.cuboid_static import normalize
    work=normalize(cube,cancel).clone();header,parents,group,indices=solver_data();prefix=[]
    def state_index():
        outer,inner=orientations(work)
        try:return indices[code(outer)]*2187+indices[code(inner)]
        except KeyError:raise ValueError('cuboid.identity_unreachable') from None
    index=state_index()
    for _ in range(header['diameter']+1):
        if cancel and cancel():raise InterruptedError()
        move=parents[index]
        if move==254:break
        if move==255:raise ValueError('cuboid.identity_unreachable')
        work.apply_move(MOVES[move]);prefix.append(MOVES[move]);index=state_index()
    if parents[index]!=254:raise ValueError('cuboid.replay_failed')
    if progress:progress(1,2)
    wanted=tuple(group['goal_colors']);colours=tuple(work.colors)
    begun=monotonic();nodes=0;seen=set()
    def visit(level,current):
        nonlocal nodes
        if cancel and cancel():raise InterruptedError()
        nodes+=1
        if seconds is not None and monotonic()-begun>seconds:raise ValueError('cuboid.search_budget')
        if current==wanted:return ()
        if level==len(group['base']) or (level,current) in seen:return None
        if len(seen)<12000:seen.add((level,current))
        point=group['base'][level];following=[]
        for beta,entry in group['transversals'][level].items():
            if current[int(beta)]!=wanted[point]:continue
            child=tuple(current[i] for i in entry['permutation'])
            following.append((sum(a!=b for a,b in zip(child,wanted)),len(entry['word']),int(beta),child,entry))
        for _,_,beta,child,entry in sorted(following):
            tail=visit(level+1,child)
            if tail is not None:return (entry,)+tail
        return None
    factors=visit(0,colours)
    if factors is None:raise ValueError('cuboid.identity_unreachable')
    word=tuple(prefix)+tuple(Move(a,l,-n%4) for entry in factors for a,l,n in reversed(entry['word']))
    replay=cube.entered()
    for move in word:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('cuboid.replay_failed')
    if progress:progress(2,2)
    return word
