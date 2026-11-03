"""Solve entered planar research-model colours on complete guarded solids.

The finite table covers the closed-shape action, including closed jumbling
words. Shape alignment is a bounded, cancellable first stage, not a promise
that every possible protruding arrangement is covered.
"""
from collections import Counter
from functools import lru_cache
from pathlib import Path
import json,time,zlib
from cube.comet_aligned import AlignedComet,generators,source_key,expand
from cube.crazy_comet import observed_colors
from cube.polyhedral import Move
from solver.lattice_data import geometry_key
from solver.polyhedral import simplify,inverse_word

ASSET=Path(__file__).resolve().parent/'data/crazy_comet_colour_group.bin'


def _invalid(message,slots=()):
    error=ValueError(message);error.locations=[dict(sticker=i) for i in slots]
    return error


@lru_cache(maxsize=1)
def placements():
    """Visible local patterns with an actual proper rigid placement."""
    from cube.appearance import ROTATIONS,transform_frame
    from cube.polyhedral import key,EDGE_AXES
    from cube.crazy_comet import structure
    masks,solids,panels=structure();owners={mask:i for i,mask in enumerate(masks)}
    normals={key(n):i for i,n in enumerate(EDGE_AXES)}
    slots={(h,f):i for i,(h,f,p) in enumerate(panels)}
    by_home=AlignedComet().geometry.pieces;result=[set() for _ in masks]
    for home,mask in enumerate(masks):
        for rotation in ROTATIONS:
            faces=tuple(normals[key(transform_frame(rotation,n))] for n in EDGE_AXES)
            target=sum(1<<faces[i] for i in range(12) if mask&(1<<i))
            destination=owners.get(target)
            if destination is None:continue
            paint={slots[destination,faces[panels[i][1]]]:panels[i][1] for i in by_home[home]}
            if set(paint)==set(by_home[destination]):
                result[destination].add(tuple(paint[i] for i in by_home[destination]))
    return tuple(frozenset(patterns) for patterns in result)


@lru_cache(maxsize=1)
def prepared():
    data=json.loads(zlib.decompress(ASSET.read_bytes()));cube=AlignedComet();n=len(cube.colors)
    macros=[[[m.axis,m.layer,m.amount] for m in word] for action,word in generators()]
    if (data.get('version')!=1 or data.get('geometry')!=geometry_key(cube.geometry)
            or data.get('source')!=source_key() or data.get('macros')!=macros
            or sorted(data.get('base',()))!=list(range(n)) or len(data.get('transversals',()))!=n):
        raise ValueError('Comet colour data do not match the guarded model')
    rows=tuple(tuple((int(beta),tuple(record['permutation']),tuple(Move(*m) for m in record['word']))
                     for beta,record in row.items()) for row in data['transversals'])
    return tuple(data['base']),rows


def validate(colors):
    cube=AlignedComet(colors);g=cube.geometry;goal=tuple(s.face for s in g.stickers)
    if any(type(c) is not int or c not in range(12) for c in colors):raise ValueError('Please enter every sticker')
    if Counter(colors)!=Counter(goal):raise ValueError('The color counts do not match this puzzle')
    # Each rigid piece retains its complete set of painted faces. Compare
    # inventories separately by orbit: a fixed face centre is not a loose leaf.
    owner={slot:home for home,slots in enumerate(g.pieces) for slot in slots};parent=list(range(len(g.pieces)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for action,word in generators():
        for slots in g.pieces:
            if slots:
                a,b=root(owner[slots[0]]),root(owner[action[slots[0]]]);parent[a]=b
    groups={}
    for home,slots in enumerate(g.pieces):
        if slots:groups.setdefault(root(home),[]).append(slots)
    for pieces in groups.values():
        if Counter(tuple(sorted(colors[i] for i in slots)) for slots in pieces)!=Counter(
                tuple(sorted(goal[i] for i in slots)) for slots in pieces):
            raise _invalid('A piece has an impossible color combination or position',tuple(i for slots in pieces for i in slots))
    for home,slots in enumerate(g.pieces):
        if tuple(colors[i] for i in slots) not in placements()[home]:
            raise _invalid('A piece has a mirrored or impossible orientation',slots)
    return cube


def solve_colours(colors,cancel=None,progress=None,seconds=30.):
    start_time=time.monotonic()
    def guard():
        if cancel and cancel():raise InterruptedError()
        if time.monotonic()-start_time>=seconds:raise TimeoutError('comet.timeout')
    guard();cube=validate(tuple(colors));start=tuple(cube.colors);goal=tuple(s.face for s in cube.geometry.stickers)
    if start==goal:return ()
    base,rows=prepared();seen=set();nodes=0
    def choices(level,current):
        guard()
        if current==goal:return iter((None,))
        if level==len(base) or (level,current) in seen:return iter(())
        # This cache only prunes revisits; bounding it cannot exclude states.
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
    if not replay.is_solved():raise ValueError('Comet colour solution replay failed')
    return result


def solve(cube,cancel=None,progress=None,seconds=45.):
    from solver.curvy_copter import normalize
    start=time.monotonic()
    if cancel and cancel():raise InterruptedError()
    if any(c<0 for c in cube.paints):raise ValueError('Please enter every sticker')
    if Counter(cube.paints)!=Counter(face for home,face,p in cube.panels):
        raise ValueError('The color counts do not match this puzzle')
    work,prefix=normalize(cube,cancel,seconds)
    tail=expand(solve_colours(observed_colors(work),cancel,progress,max(.001,seconds-(time.monotonic()-start))))
    def guard():
        if cancel and cancel():raise InterruptedError()
        if time.monotonic()-start>=seconds:raise TimeoutError('comet.timeout')
    for move in tail:work.apply_move(move,guard)
    if not work.is_solved():raise ValueError('Comet physical colour replay failed')
    return prefix+tail
