"""SQ-0, unbandaged SQ-2, and the four-ring Super SQ-1.

Radial profiles belong to the physical pieces, including SQ-2's two unequal
corner halves. They never get rebuilt as regular wedges after a turn.
"""
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import math
import random

from cube.square1 import SOLVED, Square1Cube
from cube.polyhedral import CUBE, dot

KINDS = ('square0', 'square2', 'super_square1')


@dataclass(frozen=True)
class SquareFamilyMove:
    axis: int
    amount: int = 1
    layers: int = 2

    def inverse(self, order=None):
        return type(self)(self.axis, -self.amount % 12 if self.axis < self.layers else 1, self.layers)

    def __str__(self):
        if self.axis == self.layers:
            return '/'
        values = [0]*self.layers
        value = self.amount % 12
        values[self.axis] = value-12 if value > 6 else value
        return '('+','.join(map(str, values))+')'


@dataclass(frozen=True)
class SquarePiece:
    width: int
    profile: tuple
    colors: tuple
    pair: int = 0


def layer_direction(layer, layers):
    return 1 if layer < layers/2 else -1


def _profile(layer, start, width, layers):
    direction = layer_direction(layer, layers)
    angle = -15+direction*start*30
    offsets = [0., float(width)]
    for step in range(1, width):
        if abs(((angle+direction*step*30)-45) % 90) < 1e-8:
            offsets.append(float(step))
    return tuple((step, round(1/max(abs(math.sin(math.radians(angle+direction*step*30))),
                                     abs(math.cos(math.radians(angle+direction*step*30)))),12))
                 for step in sorted(offsets))


def outline(spec, layer, start, layers):
    direction = layer_direction(layer, layers)
    return ((0.,0.),) + tuple((radius*math.sin(math.radians(-15+direction*(start+step)*30)),
                              radius*math.cos(math.radians(-15+direction*(start+step)*30)))
                             for step, radius in spec.profile)


def _spec(layer, start, width, layers, cap, pair=0):
    profile = _profile(layer, start, width, layers)
    dummy = SquarePiece(width, profile, ())
    points = outline(dummy, layer, start, layers)[1:]
    sides = tuple(max((1,2,4,5), key=lambda i: dot(CUBE[i], ((a[0]+b[0])/2,0.,(a[1]+b[1])/2)))
                  for a,b in zip(points, points[1:]))
    return SquarePiece(width, profile, (cap,)+sides, pair)


@lru_cache(maxsize=3)
def catalogue(kind):
    if kind not in KINDS:
        raise ValueError('Unknown SQ model')
    layers = 4 if kind == 'super_square1' else 2
    slots, specs = [], []
    for layer in range(layers):
        upper = layer_direction(layer,layers) == 1
        cap = 0 if upper else 3
        if kind == 'super_square1' and layer in (1,2):
            cap = -1  # Inner pieces have side stickers, not imaginary cap colours.
        if kind == 'square0':
            groups = [(start,3) for start in range(0,12,3)]
        elif kind == 'square2':
            groups = [(start,1) for start in range(12)]
        else:
            reference = SOLVED[:12] if upper else SOLVED[12:]
            groups = [(i, 2 if p&1 else 1) for i,p in enumerate(reference)
                      if reference[(i-1)%12] != p]
        ring = [-1]*12
        for start,width in groups:
            home = len(specs)
            specs.append(_spec(layer,start,width,layers,cap,int(layer in (1,2))))
            for i in range(width):
                ring[(start+i)%12] = home
        slots.extend(ring)
    return tuple(slots), tuple(specs)


class SquareFamilyCube:
    n = 3

    def __init__(self, kind='square0', slots=None, middle=0):
        target, self.specs = catalogue(kind)
        self.puzzle_kind = kind
        self.layer_count = 4 if kind == 'super_square1' else 2
        self.slots = tuple(target if slots is None else slots)
        self.middle = int(middle)

    @classmethod
    def solved(cls, kind='square0'):
        return cls(kind)

    def clone(self):
        return type(self)(self.puzzle_kind,self.slots,self.middle)

    entered = clone

    def move(self, axis, amount=1):
        return SquareFamilyMove(axis,amount,self.layer_count)

    def layer_direction(self, layer):
        return layer_direction(layer,self.layer_count)

    def piece_colors(self, piece):
        colors = self.specs[piece].colors
        return colors[0],colors[1:]

    def outline(self, layer, start, width, piece):
        return outline(self.specs[piece],layer,start,self.layer_count)

    def groups(self):
        return tuple((layer,i,self.specs[p].width,p)
                     for layer in range(self.layer_count)
                     for i,p in enumerate(self.slots[layer*12:layer*12+12])
                     if self.slots[layer*12+(i-1)%12] != p)

    def can_slice(self):
        return all(self.slots[layer*12+a] != self.slots[layer*12+b]
                   for layer in range(self.layer_count) for a,b in ((11,0),(5,6)))

    def apply_move(self, move):
        if move.layers != self.layer_count:
            raise ValueError('sq.error.move')
        if move.axis == self.layer_count:
            if not self.can_slice():
                raise ValueError('square1.error.blocked')
            slots = list(self.slots)
            for top in range(self.layer_count//2):
                bottom = self.layer_count-1-top
                a,b = top*12+6,bottom*12
                slots[a:a+6],slots[b:b+6] = self.slots[b:b+6],self.slots[a:a+6]
            self.slots = tuple(slots)
            self.middle ^= 1
        elif 0 <= move.axis < self.layer_count:
            if self.puzzle_kind == 'square0' and move.amount % 3:
                raise ValueError('sq.error.quarter')
            start = move.axis*12
            ring = self.slots[start:start+12]
            amount = move.amount % 12
            self.slots = self.slots[:start]+ring[amount:]+ring[:amount]+self.slots[start+12:]
        else:
            raise ValueError('sq.error.move')

    def apply_moves(self, moves):
        for move in moves:
            self.apply_move(move)

    def validate(self):
        if len(self.slots) != 12*self.layer_count or self.middle not in (0,1):
            raise ValueError('sq.error.incomplete')
        if any(p not in range(len(self.specs)) for p in self.slots):
            raise ValueError('sq.error.incomplete')
        counts = Counter(self.slots)
        if any(counts[i] != spec.width for i,spec in enumerate(self.specs)):
            raise ValueError('square1.error.duplicate')
        starts = Counter()
        for layer,start,width,piece in self.groups():
            starts[piece] += 1
            if any(self.slots[layer*12+(start+i)%12] != piece for i in range(width)):
                raise ValueError('square1.error.split')
            if self.puzzle_kind == 'super_square1' and self.specs[piece].pair != int(layer in (1,2)):
                raise ValueError('sq.error.orbit')
            if self.puzzle_kind == 'square0' and start % 3:
                raise ValueError('sq.error.quarter')
        if any(starts[i] != 1 for i in range(len(self.specs))):
            raise ValueError('square1.error.split')
        return self

    def is_solved(self):
        goal = catalogue(self.puzzle_kind)[0]
        return self.middle == 0 and len(self.slots) == len(goal) and all(
            self.specs[a] == self.specs[b] for a,b in zip(self.slots,goal))

    def scramble(self, length=20, seed=None):
        rng = random.Random(seed)
        step = 3 if self.puzzle_kind == 'square0' else 1
        for _ in range(length):
            for layer in range(self.layer_count):
                ring = self.slots[layer*12:layer*12+12]
                legal = [k for k in range(0,12,step) if ring[(k-1)%12] != ring[k]
                         and ring[(k+5)%12] != ring[(k+6)%12]]
                self.apply_move(self.move(layer,rng.choice(legal)))
            self.apply_move(self.move(self.layer_count))
        return self

    def projection(self, pair):
        """Label a Super pair with the existing SQ-1 solver's exact ID convention."""
        top,bottom = (0,3) if pair == 0 else (1,2)
        mapping = {}
        goal = catalogue('super_square1')[0]
        for layer,reference in ((top,SOLVED[:12]),(bottom,SOLVED[12:])):
            mapping.update(zip(goal[layer*12:layer*12+12],reference))
        return Square1Cube(tuple(mapping[p] for layer in (top,bottom)
                                 for p in self.slots[layer*12:layer*12+12]), self.middle)
