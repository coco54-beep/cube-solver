"""Closed cubic actions for the Drawing3 regular-turn profile."""
from functools import lru_cache
from cube.twins_state import TwinsState,AXES
from cube.twins_cad_material import fingerprint
from cube.polyhedral import CUBE,Move,Spec,Geometry,Sticker
from cube.pisces_aligned import AlignedPisces,expand_circuits
from cube.crazy_comet import observed_colors

source_key=fingerprint


@lru_cache(maxsize=1)
def generators():
    c=TwinsState();rows=[]
    for axis in range(20):
        word=(Move(axis,0,180. if axis<12 else 120.),)
        rows.append((c.clone().apply_moves(word).aligned_permutation(),word))
    return tuple(rows)


@lru_cache(maxsize=1)
def geometry():
    c=TwinsState();g=c.geometry;rows=generators()
    layers=tuple((tuple(h for h,slots in enumerate(g.pieces) if any(a[i]!=i for i in slots)),) for a,w in rows)
    return Geometry(Spec('_twins_aligned',3,CUBE,AXES,(),6,axis_steps=(3,)*12+(2,)*8),
                    tuple(Sticker(h,f,p) for h,f,p in c.panels),g.pieces,g.centres,tuple((a,) for a,w in rows),layers)


class AlignedTwins(AlignedPisces):
    puzzle_kind='_twins_aligned'
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=192:raise ValueError('Wrong Drawing3 Twins panel count')


def expand(word):return expand_circuits(word,generators())


def scrambled(seed=None,length=30,cancel=None,jumble=False):
    from random import Random
    from time import monotonic
    rng=Random(seed);c=TwinsState();previous=-1;deadline=monotonic()+15.
    for _ in range(length):
        if cancel and cancel():raise InterruptedError()
        if monotonic()>=deadline:raise TimeoutError('copter.scramble_timeout')
        move=rng.choice([Move(a,0,t) for a in range(20) if a!=previous for t in ((180.,) if a<12 else (120.,-120.))])
        c.apply_move(move);previous=move.axis
    if jumble and length:
        from cube.cad_copter_scramble import deform
        deform(c,rng,cancel,deadline)
    return c
