"""Exact closed regular turns on the Flower Copter material profile."""
import hashlib
from functools import lru_cache
from cube.flower_copter import FlowerCopterCube,structure,AXES,cuts
from cube.polyhedral import Move,Spec,Geometry,Sticker
from cube.pisces_aligned import AlignedPisces,expand_circuits
from cube.crazy_comet import observed_colors


@lru_cache(maxsize=1)
def source_key():return hashlib.sha256(repr((cuts(),structure()[0],structure()[2])).encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def generators():
    c=FlowerCopterCube();rows=[]
    for axis in range(20):
        word=(Move(axis,0,180. if axis<12 else 120.),)
        rows.append((c.clone().apply_moves(word).aligned_permutation(),word))
    return tuple(rows)


@lru_cache(maxsize=1)
def geometry():
    c=FlowerCopterCube();g=c.geometry;rows=generators()
    layers=tuple((tuple(h for h,slots in enumerate(g.pieces) if any(a[i]!=i for i in slots)),) for a,w in rows)
    return Geometry(Spec('_flower_copter_aligned',3,g.spec.normals,AXES,(),6,axis_steps=(3,)*12+(2,)*8),
                    tuple(Sticker(h,f,p) for h,f,p in c.panels),g.pieces,g.centres,tuple((a,) for a,w in rows),layers)


class AlignedFlowerCopter(AlignedPisces):
    puzzle_kind='_flower_copter_aligned'
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=len(self.geometry.stickers):raise ValueError('Wrong Flower Copter panel count')


def expand(word):return expand_circuits(word,generators())


def scrambled(seed=None,length=30,cancel=None,*,shape=False):
    from random import Random
    from time import monotonic
    rng=Random(seed);cube=FlowerCopterCube();previous=-1;deadline=monotonic()+15.
    for _ in range(length):
        if cancel and cancel():raise InterruptedError()
        if monotonic()>=deadline:raise TimeoutError('copter.scramble_timeout')
        choices=[Move(a,0,t) for a in range(20) if a!=previous for t in ((180.,) if a<12 else (120.,-120.))]
        move=rng.choice(choices);cube.apply_move(move);previous=move.axis
    if shape and length:
        from cube.cad_copter_scramble import deform
        deform(cube,rng,cancel,deadline)
    return cube
