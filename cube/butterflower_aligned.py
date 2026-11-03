"""Whole-material actions for the radius-one Butterflower profile."""
import hashlib
from functools import lru_cache
from cube.butterflower import ButterflowerCube
from cube.butterflower_material import AXES,cuts,structure
from cube.polyhedral import Move,Spec,Geometry,Sticker
from cube.pisces_aligned import AlignedPisces,expand_circuits
from cube.crazy_comet import observed_colors


@lru_cache(maxsize=1)
def source_key():return hashlib.sha256(repr((cuts(),structure()[0],structure()[2])).encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def generators():
    import json,zlib
    from pathlib import Path
    from cube.butterflower_material import fingerprint
    c=ButterflowerCube();rows=[]
    for axis in range(20):
        word=(Move(axis,0,180. if axis<12 else 120.),)
        rows.append((c.clone().apply_moves(word).aligned_permutation(),word))
    data=json.loads(zlib.decompress((Path(__file__).parent/'data/butterflower_jumbles.bin').read_bytes()))
    if data.get('version')!=1 or data.get('source')!=fingerprint():raise ValueError('Butterflower exchange cache mismatch')
    for record in data['rows']:
        action=tuple(record['action']);word=tuple(Move(*m) for m in record['word'])
        if (sorted(action)!=list(range(len(c.panels))) or len(word)!=5
                or any(action[action[i]]!=i for i in range(len(action)))):
            raise ValueError('Invalid Butterflower exchange certificate')
        rows.append((action,word))
    return tuple(rows)


@lru_cache(maxsize=1)
def geometry():
    c=ButterflowerCube();g=c.geometry;rows=generators()
    layers=tuple((tuple(h for h,s in enumerate(g.pieces) if any(a[i]!=i for i in s)),) for a,w in rows)
    axes=tuple(AXES[w[len(w)//2].axis] for a,w in rows)
    steps=(3,)*12+(2,)*8+(3,)*(len(rows)-20)
    return Geometry(Spec('_butterflower_aligned',3,g.spec.normals,axes,(),6,axis_steps=steps),
                    tuple(Sticker(h,f,p) for h,f,p in c.panels),g.pieces,g.centres,
                    tuple((a,) for a,w in rows),layers)


class AlignedButterflower(AlignedPisces):
    puzzle_kind='_butterflower_aligned'
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=len(self.geometry.stickers):raise ValueError('Wrong Butterflower field count')


def expand(word):return expand_circuits(word,generators())


def scrambled(seed=None,length=30,cancel=None,*,shape=True):
    from random import Random
    from time import monotonic
    rng=Random(seed);cube=ButterflowerCube();previous=-1;options=generators();deadline=monotonic()+12
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()>deadline:raise TimeoutError('copter.scramble_timeout')
    for _ in range(length):
        guard();index=rng.choice([i for i in range(len(options)) if i!=previous]);previous=index
        for move in options[index][1]:cube.apply_move(move,guard)
    if shape and length:
        # Leave the observed outline at a petal-exchange preparation, rather
        # than merely colouring a cube. Every prefix is whole-material legal.
        word=rng.choice(options[20:])[1]
        for move in word[:rng.choice((1,2,3,4))]:cube.apply_move(move,guard)
    return cube
