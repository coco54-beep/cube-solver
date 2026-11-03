"""Closed SunCube II tools derived on its own whole material."""
from functools import lru_cache
from itertools import combinations,product
import hashlib
from cube.suncube import SunCube,structure
from cube.polyhedral import Move,Spec,Geometry,Sticker,EDGE_AXES,dot
from cube.curvy_copter import JUMBLE
from cube.copter_aligned import compact
from cube.crazy_comet import observed_colors


@lru_cache(maxsize=1)
def source_key():return hashlib.sha256(repr(structure()).encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def generators():
    base=SunCube();words=[(Move(a,0,180.),) for a in range(12)]
    for target,n in enumerate(EDGE_AXES):
        for a,b in combinations(range(12),2):
            if abs(dot(EDGE_AXES[a],n)+.5)>1e-8 or abs(dot(EDGE_AXES[b],n)+.5)>1e-8:continue
            if abs(dot(EDGE_AXES[a],EDGE_AXES[b])+.5)>1e-8:continue
            for sa,sb in product((-1,1),repeat=2):
                prefix=(Move(a,0,sa*JUMBLE),Move(b,0,sb*JUMBLE))
                words.append(prefix+(Move(target,0,180.),)+tuple(Move(m.axis,0,-m.amount) for m in reversed(prefix)))
    found={}
    for word in words:
        work=base.clone()
        try:work.apply_moves(word);action=work.aligned_permutation()
        except ValueError:continue
        if action not in found or len(word)<len(found[action]):found[action]=word
    return tuple(found.items())


@lru_cache(maxsize=1)
def geometry():
    c=SunCube();g=c.geometry;rows=generators()
    layers=tuple((tuple(h for h,slots in enumerate(g.pieces) if any(a[i]!=i for i in slots)),) for a,w in rows)
    return Geometry(Spec('_suncube_aligned',3,g.spec.normals,tuple(EDGE_AXES[w[len(w)//2].axis] for a,w in rows),(),2),
                    tuple(Sticker(h,f,p) for h,f,p in c.panels),g.pieces,g.centres,tuple((a,) for a,w in rows),layers)


class AlignedSunCube:
    puzzle_kind='_suncube_aligned'
    color_count=6
    n=3
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=len(self.geometry.stickers):raise ValueError('Wrong SunCube panel count')
    def clone(self):return type(self)(self.colors)
    entered=clone
    def moves(self):return tuple(Move(i) for i in range(len(generators())))
    def apply_move(self,move):
        self.colors=[self.colors[i] for i in self.geometry.inverse_permutation(move)];return self
    def is_solved(self):return self.colors==[s.face for s in self.geometry.stickers]


def expand(word):return compact(tuple(atom for m in word if m.amount%2 for atom in generators()[m.axis][1]))


def scrambled(seed=None,length=30,cancel=None,jumble=True):
    from random import Random
    from time import monotonic
    rng=Random(seed);c=SunCube();rows=generators();previous=None;deadline=monotonic()+20
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()>deadline:raise TimeoutError('copter.scramble_timeout')
    for _ in range(length):
        guard();i=rng.choice([j for j in range(len(rows)) if j!=previous]);previous=i
        for m in rows[i][1]:c.apply_move(m,guard)
    if jumble:
        choices=[m for m in c.moves() if m.amount!=180.];rng.shuffle(choices)
        for m in choices:
            guard()
            if c.can_apply(m):c.apply_move(m);break
    return c
