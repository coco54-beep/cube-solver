"""Closed shape actions for the scooped, unbandaged LanLan Comet."""
from functools import lru_cache
from itertools import combinations,product
import hashlib
from cube.polyhedral import EDGE_AXES,Move,dot,Spec,Geometry,Sticker
from cube.curvy_copter import JUMBLE
from cube.lanlan_comet import LanlanCometCube,structure,CUT


@lru_cache(maxsize=1)
def source_key():return hashlib.sha256(repr((CUT,structure())).encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def generators():
    cube=LanlanCometCube();found={};words=[(Move(axis,0,180.),) for axis in range(12)]
    # Unbandaging adds one-preparation exchanges absent from the retained
    # planar model. Omitting them falsely rejects reachable entered colours.
    for a in range(12):
        for b in range(12):
            if a==b:continue
            for angle in (JUMBLE,-JUMBLE,180-JUMBLE,JUMBLE-180):
                words.append((Move(a,0,angle),Move(b,0,180.),Move(a,0,-angle)))
    for target,n in enumerate(EDGE_AXES):
        neighbours=[i for i,a in enumerate(EDGE_AXES) if abs(dot(a,n)-.5)<1e-8]
        for a,b in combinations(neighbours,2):
            if dot(EDGE_AXES[a],EDGE_AXES[b])>-.49:continue
            for sa,sb in product((-1,1),repeat=2):
                words.append((Move(a,0,sa*JUMBLE),Move(b,0,sb*JUMBLE),Move(target,0,180.),
                              Move(b,0,-sb*JUMBLE),Move(a,0,-sa*JUMBLE)))
    for word in words:
        work=cube.clone()
        try:work.apply_moves(word);action=work.aligned_permutation()
        except ValueError:continue
        if any(action[action[s]]!=s for s in range(len(action))):raise ValueError('Non-involutory Comet action')
        if action not in found or len(word)<len(found[action]):found[action]=word
    return tuple(found.items())


@lru_cache(maxsize=1)
def geometry():
    cube=LanlanCometCube();g=cube.geometry;rows=generators()
    layers=tuple((tuple(p for p,slots in enumerate(g.pieces) if any(action[i]!=i for i in slots)),)
                 for action,word in rows)
    return Geometry(Spec('_lanlan_comet_aligned',3,EDGE_AXES,
                         tuple(EDGE_AXES[w[len(w)//2].axis] for a,w in rows),(),2),
                    tuple(Sticker(h,f,p) for h,f,p in cube.panels),g.pieces,g.centres,
                    tuple((action,) for action,word in rows),layers)


class AlignedComet:
    puzzle_kind='_lanlan_comet_aligned'
    n=3
    color_count=13
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=len(self.geometry.stickers):raise ValueError('Wrong Comet panel count')
    def clone(self):return type(self)(self.colors)
    entered=clone
    def moves(self):return tuple(Move(i) for i in range(len(generators())))
    def apply_move(self,move):
        inv=self.geometry.inverse_permutation(move);self.colors=[self.colors[i] for i in inv];return self
    def is_solved(self):return self.colors==[s.face for s in self.geometry.stickers]


def expand(word):
    from cube.copter_aligned import compact
    return compact(tuple(m for move in word if move.amount%2 for m in generators()[move.axis][1]))


def scrambled(seed=None,length=30,cancel=None,jumble=True):
    from random import Random
    from time import monotonic
    rng=Random(seed);cube=LanlanCometCube();options=generators();previous=None;deadline=monotonic()+12
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()>deadline:raise TimeoutError('copter.scramble_timeout')
    for _ in range(length):
        guard();index=rng.choice([i for i in range(len(options)) if i!=previous]);previous=index
        for move in options[index][1]:cube.apply_move(move,guard)
    for _ in range(6 if jumble else 0):
        choices=list(cube.moves());rng.shuffle(choices)
        for move in choices:
            guard()
            try:cube.apply_move(move,guard);break
            except ValueError:continue
    return cube
