"""Curvy Hexagram circuits verified against its independent tetrahedral shell."""
from functools import lru_cache
import hashlib
from cube.hexagram import HexagramCube,structure
from cube.pisces_aligned import AlignedPisces,verified_generators,action_order,expand_circuits
from cube.polyhedral import Move,Spec,Geometry,Sticker
from cube.crazy_comet import observed_colors


@lru_cache(maxsize=1)
def source_key():return hashlib.sha256(repr(structure()).encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def generators():return verified_generators(HexagramCube)


@lru_cache(maxsize=1)
def geometry():
    c=HexagramCube();g=c.geometry;rows=generators()
    steps=tuple(6//action_order(a) for a,w in rows)
    layers=tuple((tuple(h for h,slots in enumerate(g.pieces) if any(a[i]!=i for i in slots)),) for a,w in rows)
    return Geometry(Spec('_hexagram_aligned',3,g.spec.normals,tuple(c.turn_axes[w[0].axis] for a,w in rows),(),6,axis_steps=steps),
                    tuple(Sticker(h,f,p) for h,f,p in c.panels),g.pieces,g.centres,tuple((a,) for a,w in rows),layers)


class AlignedHexagram(AlignedPisces):
    puzzle_kind='_hexagram_aligned'
    color_count=4
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=len(self.geometry.stickers):raise ValueError('Wrong Hexagram panel count')


def expand(word):return expand_circuits(word,generators())


def scrambled(seed=None,length=30,cancel=None,jumble=True):
    from random import Random
    from time import monotonic
    rng=Random(seed);c=HexagramCube();rows=generators();previous=None;deadline=monotonic()+15
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()>deadline:raise TimeoutError('copter.scramble_timeout')
    for _ in range(length):
        guard();i=rng.choice([j for j in range(len(rows)) if j!=previous]);previous=i
        for m in rows[i][1]:c.apply_move(m,guard)
    if jumble:
        choices=list(c.moves());rng.shuffle(choices)
        for m in choices:
            guard()
            if c.can_apply(m):c.apply_move(m);break
    return c
