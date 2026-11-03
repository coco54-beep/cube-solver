"""Observed-state solver for the scooped LanLan Comet, with guarded replay.

Shape repair is bounded. The finite closed-shape colour stage uses its own
verified action table; the retained planar puzzle's table is never reused.
"""
from collections import Counter
from functools import lru_cache
from pathlib import Path
import json,time,zlib
from cube.lanlan_comet import LanlanCometCube,placements
from cube.lanlan_comet_aligned import AlignedComet,generators,source_key,expand
from cube.crazy_comet import observed_colors
from cube.polyhedral import Move
from solver.lattice_data import geometry_key
from solver.polyhedral import simplify,inverse_word

ASSET=Path(__file__).resolve().parent/'data/lanlan_comet_colour_group.bin'


@lru_cache(maxsize=1)
def prepared():
    data=json.loads(zlib.decompress(ASSET.read_bytes()));cube=AlignedComet();n=len(cube.colors)
    macros=[[[m.axis,m.layer,m.amount] for m in word] for action,word in generators()]
    if (data.get('version')!=1 or data.get('geometry')!=geometry_key(cube.geometry)
            or data.get('source')!=source_key() or data.get('macros')!=macros
            or sorted(data.get('base',()))!=list(range(n)) or len(data.get('transversals',()))!=n):
        raise ValueError('LanLan Comet data do not match the guarded model')
    rows=tuple(tuple((int(beta),tuple(record['permutation']),tuple(Move(*m) for m in record['word']))
                     for beta,record in row.items()) for row in data['transversals'])
    return tuple(data['base']),rows


@lru_cache(maxsize=1)
def local_patterns():
    cube=LanlanCometCube();result=[set() for _ in cube.solids]
    for home in range(len(cube.solids)):
        for destination,frame,mapping in placements(home):
            pattern={target:cube.panels[source][1] for source,target in mapping}
            slots=cube.geometry.pieces[destination]
            result[destination].add(tuple(pattern[i] for i in slots))
    return tuple(frozenset(patterns) for patterns in result)


def validate(colors):
    cube=AlignedComet(colors);g=cube.geometry;goal=tuple(s.face for s in g.stickers)
    if any(type(c) is not int or c not in range(13) for c in colors):raise ValueError('Please enter every sticker')
    if Counter(colors)!=Counter(goal):raise ValueError('The color counts do not match this puzzle')
    for home,slots in enumerate(g.pieces):
        if tuple(colors[i] for i in slots) not in local_patterns()[home]:
            error=ValueError('A piece has a mirrored or impossible orientation')
            error.locations=[dict(sticker=i) for i in slots];raise error
    # Inventory constraints apply separately to each whole-piece orbit.
    owner={s:h for h,slots in enumerate(g.pieces) for s in slots};parent=list(range(len(g.pieces)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for action,word in generators():
        for slots in g.pieces:
            if slots:parent[root(owner[slots[0]])]=root(owner[action[slots[0]]])
    groups={}
    for home,slots in enumerate(g.pieces):
        if slots:groups.setdefault(root(home),[]).append(slots)
    for pieces in groups.values():
        if Counter(tuple(sorted(colors[i] for i in slots)) for slots in pieces)!=Counter(
                tuple(sorted(goal[i] for i in slots)) for slots in pieces):
            error=ValueError('A piece has an impossible color combination or position')
            error.locations=[dict(sticker=i) for slots in pieces for i in slots];raise error
    return cube


def piece_labels(colors):
    """Recover unique physical identities from complete colour combinations.

    These are observations, not hidden numbers the user has to enter. Every
    solved visible piece has a distinct set of colours and no repeated colour
    on its own panels, including the 24 gold-tipped three-colour pieces.
    """
    cube=AlignedComet();goal=tuple(cube.colors);inventory={};result=[None]*len(goal)
    for slots in cube.geometry.pieces:
        if not slots:continue
        signature=tuple(sorted(goal[i] for i in slots))
        if signature in inventory:raise ValueError('Ambiguous Comet physical inventory')
        inventory[signature]={goal[i]:i for i in slots}
    seen=set()
    for slots in cube.geometry.pieces:
        if not slots:continue
        signature=tuple(sorted(colors[i] for i in slots))
        if signature not in inventory or signature in seen:
            raise ValueError('A piece has an impossible color combination or position')
        seen.add(signature)
        for i in slots:result[i]=inventory[signature][colors[i]]
    return tuple(result)


def solve_colours(colors,cancel=None,progress=None,seconds=30.):
    started=time.monotonic()
    def guard():
        if cancel and cancel():raise InterruptedError()
        if time.monotonic()-started>=seconds:raise TimeoutError('comet.timeout')
    guard();cube=validate(tuple(colors));start=piece_labels(cube.colors);goal=tuple(range(len(start)))
    if start==goal:return ()
    base,rows=prepared();seen=set();nodes=0
    def choices(level,current):
        guard()
        if current==goal:return iter((None,))
        if level==len(base) or (level,current) in seen:return iter(())
        if len(seen)<20000:seen.add((level,current))
        k=base[level];options=[]
        for beta,permutation,word in rows[level]:
            if current[beta]!=goal[k]:continue
            child=tuple(current[i] for i in permutation)
            options.append((sum(a!=b for a,b in zip(child,goal)),len(word),beta,child,word))
        options.sort(key=lambda row:row[:3]);return iter(options)
    factors=[];stack=[(0,start,choices(0,start))];found=None
    while stack:
        guard();level,current,options=stack[-1];item=next(options,False)
        if item is None:found=tuple(factors);break
        if item is False:
            stack.pop()
            if factors:factors.pop()
            continue
        _,_,_,child,word=item;factors.append(word);nodes+=1
        stack.append((level+1,child,choices(level+1,child)))
        if progress and nodes%128==0:progress(-1,0)
    if found is None:raise ValueError('The entered puzzle is not a legal state')
    result=simplify(tuple(move for word in found for move in inverse_word(word,2)),2)
    replay=cube.clone()
    for move in result:guard();replay.apply_move(move)
    if not replay.is_solved():raise ValueError('LanLan Comet colour replay failed')
    from solver.solution_loops import shorten_polyhedral_word
    result=shorten_polyhedral_word(cube,result,cancel)
    return result


def solve(cube,cancel=None,progress=None,seconds=45.):
    from solver.curvy_copter import normalize
    started=time.monotonic()
    if cancel and cancel():raise InterruptedError()
    if any(c<0 for c in cube.paints):raise ValueError('Please enter every sticker')
    if Counter(cube.paints)!=Counter(face for home,face,p in cube.panels):
        raise ValueError('The color counts do not match this puzzle')
    work,prefix=normalize(cube,cancel,seconds)
    tail=expand(solve_colours(observed_colors(work),cancel,progress,
                              max(.001,seconds-(time.monotonic()-started))))
    def guard():
        if cancel and cancel():raise InterruptedError()
        if time.monotonic()-started>=seconds:raise TimeoutError('comet.timeout')
    for move in tail:work.apply_move(move,guard)
    if not work.is_solved():raise ValueError('LanLan Comet physical replay failed')
    return prefix+tail
