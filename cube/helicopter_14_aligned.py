"""Closed, full-material fourteen-face Helicopter actions including jumbling."""
from functools import lru_cache
import math,hashlib
from itertools import combinations,product
from cube.edge_jumbling import Helicopter14Cube
from cube.polyhedral import Move,Spec,Geometry,Sticker,EDGE_AXES,dot
from cube.curvy_copter import JUMBLE
from cube.pisces_aligned import AlignedPisces,expand_circuits


@lru_cache(maxsize=1)
def source_key():
    c=Helicopter14Cube()
    return hashlib.sha256(repr((c.solids,c.panels,c.cut_bounds,'closed-jumbling-v1')).encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def generators():
    base=Helicopter14Cube();found={}
    words=[(Move(a,0,180.),) for a in range(12)]
    for target,n in enumerate(EDGE_AXES):
        adjacent=[a for a,m in enumerate(EDGE_AXES) if abs(dot(n,m)-.5)<1e-8]
        for a,b in combinations(adjacent,2):
            if dot(EDGE_AXES[a],EDGE_AXES[b])>-.49:continue
            for sa,sb in product((-1,1),repeat=2):
                words.append((Move(a,0,sa*JUMBLE),Move(b,0,sb*JUMBLE),Move(target,0,180.),
                              Move(b,0,-sb*JUMBLE),Move(a,0,-sa*JUMBLE)))
    for word in words:
        cube=base.clone()
        try:cube.apply_moves(word);action=cube.aligned_permutation()
        except ValueError:continue
        if any(action[action[i]]!=i for i in range(len(action))):raise ValueError('Fourteen-face exchange is not an involution')
        found.setdefault(action,word)
    return tuple(found.items())


@lru_cache(maxsize=1)
def geometry():
    c=Helicopter14Cube();g=c.geometry;rows=generators()
    axes=tuple(EDGE_AXES[w[len(w)//2].axis] for p,w in rows)
    layers=tuple((tuple(h for h,s in enumerate(g.pieces) if any(p[i]!=i for i in s)),) for p,w in rows)
    return Geometry(Spec('_helicopter_14_jumbling',3,c.normals,axes,(),6,axis_steps=(3,)*len(rows)),
                    tuple(Sticker(h,min(f,6),p) for h,f,p in c.panels),g.pieces,g.centres,
                    tuple((p,) for p,w in rows),layers)


class AlignedHelicopter14(AlignedPisces):
    puzzle_kind='_helicopter_14_jumbling'
    color_count=7
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=32:raise ValueError('Wrong fourteen-face Helicopter field count')


def expand(word):return expand_circuits(word,generators())


def observed_colors(cube):
    result=[None]*len(cube.panels)
    for source,target in enumerate(cube.aligned_permutation()):result[target]=cube.paints[source]
    return tuple(result)


def scrambled(seed=None,length=30,cancel=None,jumble=True):
    from random import Random
    from time import monotonic
    rng=Random(seed);c=Helicopter14Cube();rows=generators();previous=-1;deadline=monotonic()+15
    exchanges=[i for i,(p,w) in enumerate(rows) if len(w)==5]
    if not exchanges:raise ValueError('No guarded fourteen-face exchanges')
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()>=deadline:raise TimeoutError('copter.scramble_timeout')
    for step in range(length):
        guard();pool=exchanges if step%3==0 else range(len(rows))
        index=rng.choice([i for i in pool if i!=previous]);previous=index
        for move in rows[index][1]:c.apply_move(move,guard)
    if jumble and length:
        # Closed exchanges mix colours first; one genuine partial preparation
        # leaves a recoverable non-cubic shell without a stored inverse word.
        c.apply_move(rows[rng.choice(exchanges)][1][0],guard)
    return c
