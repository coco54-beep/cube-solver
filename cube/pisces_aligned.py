"""Closed Pisces circuits, independently found and whole-material verified."""
from functools import lru_cache
import hashlib,math
from cube.pisces import PiscesCube,AXES,ANGLE1,ANGLE2,structure
from cube.polyhedral import Move,Spec,Geometry,Sticker,key
from cube.appearance import ROTATIONS,transform_frame
from cube.copter_aligned import compact
from cube.crazy_comet import observed_colors

SEEDS=(
    ((4,2),(7,2),(8,-2),(7,-2),(7,-2),(4,-2),(7,2),(8,2)),
    ((4,2),(5,2),(2,-2),(5,-2),(2,2),(4,-2),(7,-2),(0,2),(6,-2),(0,-2),(6,2),(7,2)),
    ((3,2),(4,2),(7,-2),(4,-2),(4,-2),(3,-2),(4,2),(6,-2),(0,2),(6,2),(6,2),(7,2),(6,-2),(0,-2)),
)


def action_order(action):
    seen=set();lengths=[]
    for start in range(len(action)):
        if start in seen:continue
        p=start;length=0
        while p not in seen:seen.add(p);length+=1;p=action[p]
        lengths.append(length)
    return math.lcm(*lengths)


@lru_cache(maxsize=1)
def source_key():return hashlib.sha256(repr(structure()).encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def generators():
    return verified_generators(PiscesCube)


def verified_generators(factory):
    axes={key(n):i for i,n in enumerate(AXES)};found={}
    for frame in ROTATIONS:
        mapped=tuple(axes.get(key(transform_frame(frame,n))) for n in AXES)
        if None in mapped:continue
        for seed in SEEDS:
            word=compact(tuple(Move(mapped[a],0,math.copysign(ANGLE1 if abs(k)==1 else ANGLE2,k)) for a,k in seed))
            work=factory().apply_moves(word);action=work.aligned_permutation()
            if action_order(action) not in (2,3,6):raise ValueError('Unexpected Pisces circuit order')
            if action not in found or len(word)<len(found[action]):found[action]=word
    return tuple(found.items())


@lru_cache(maxsize=1)
def geometry():
    c=PiscesCube();g=c.geometry;rows=generators()
    steps=tuple(6//action_order(a) for a,w in rows)
    layers=tuple((tuple(h for h,slots in enumerate(g.pieces) if any(a[i]!=i for i in slots)),) for a,w in rows)
    return Geometry(Spec('_pisces_aligned',3,g.spec.normals,tuple(AXES[w[0].axis] for a,w in rows),(),6,axis_steps=steps),
                    tuple(Sticker(h,f,p) for h,f,p in c.panels),g.pieces,g.centres,tuple((a,) for a,w in rows),layers)


class AlignedPisces:
    puzzle_kind='_pisces_aligned'
    color_count=6
    n=3
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=len(self.geometry.stickers):raise ValueError('Wrong Pisces panel count')
    def clone(self):return type(self)(self.colors)
    entered=clone
    def moves(self):
        return tuple(Move(i,0,step) for i in range(len(self.geometry.layers)) for step in
                     (self.geometry.spec.step(i),6-self.geometry.spec.step(i)) if step!=6)
    def apply_move(self,move):
        self.colors=[self.colors[i] for i in self.geometry.inverse_permutation(move)];return self
    def is_solved(self):return self.colors==[s.face for s in self.geometry.stickers]


def expand(word):
    return expand_circuits(word,generators())


def expand_circuits(word,rows):
    output=[]
    for move in word:
        order=action_order(rows[move.axis][0]);step=6//order;count=round(move.amount/step)%order
        raw=rows[move.axis][1]
        if count>order//2:raw=tuple(Move(m.axis,0,-m.amount) for m in reversed(raw));count=order-count
        output.extend(raw*count)
    return compact(tuple(output))


def scrambled(seed=None,length=30,cancel=None,jumble=True):
    from random import Random
    from time import monotonic
    rng=Random(seed);c=PiscesCube();rows=generators();previous=None;deadline=monotonic()+12
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
