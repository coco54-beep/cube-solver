"""Square-1 state with variable-width pieces and state-dependent slice legality.

Piece numbering follows cs0x7f/sq12phase (GPLv3): even IDs are edges and
odd IDs are corners. Opposite layers run in opposite physical directions.
"""
from collections import Counter
from dataclasses import dataclass
import random
import math
from functools import lru_cache

SOLVED=tuple(int(c,16) for c in '011233455677998bbaddcffe')


@lru_cache(maxsize=16)
def piece_colors(piece):
    """Cap and ordered side colours, in each layer's own viewing direction."""
    from cube.polyhedral import CUBE,dot
    layer,start,width,_=next(p for p in Square1Cube().groups() if p[3]==piece)
    direction=1 if layer==0 else -1
    angle=math.radians(-15+direction*start*30)
    end=angle+direction*math.radians(width*30)
    radius=1/math.cos(math.pi/12)
    outline=[(radius*math.sin(angle),radius*math.cos(angle))]
    if width==2:
        middle=(angle+end)/2
        outline.append((math.sqrt(2)*math.sin(middle),math.sqrt(2)*math.cos(middle)))
    outline.append((radius*math.sin(end),radius*math.cos(end)))
    sides=tuple(max((1,2,4,5),key=lambda i:dot(CUBE[i],((a[0]+b[0])/2,0.,(a[1]+b[1])/2)))
                for a,b in zip(outline,outline[1:]))
    return (0 if layer==0 else 3),sides


@dataclass(frozen=True)
class Square1Move:
    axis: int  # 0 top, 1 bottom, 2 slice
    amount: int=1

    def inverse(self,order=None):
        return Square1Move(self.axis,(-self.amount)%12 if self.axis<2 else 1)

    def __str__(self):
        if self.axis==2:
            return '/'
        value=self.amount%12
        if value>6:
            value-=12
        return f'({value},0)' if self.axis==0 else f'(0,{value})'


class Square1Cube:
    puzzle_kind='square1'
    n=3

    def __init__(self,slots=SOLVED,middle=0):
        self.slots=tuple(slots)
        self.middle=int(middle)

    @classmethod
    def solved(cls):
        return cls()

    def clone(self):
        return type(self)(self.slots,self.middle)

    entered=clone

    def is_solved(self):
        return self.slots==SOLVED and self.middle==0

    def can_slice(self):
        return all(self.slots[a]!=self.slots[b] for a,b in ((11,0),(5,6),(23,12),(17,18)))

    def apply_move(self,move):
        if move.axis==2:
            if not self.can_slice():
                raise ValueError('square1.error.blocked')
            p=self.slots
            self.slots=p[:6]+p[12:18]+p[6:12]+p[18:]
            self.middle^=1
        elif move.axis in (0,1):
            start=move.axis*12
            part=self.slots[start:start+12]
            k=move.amount%12
            part=part[k:]+part[:k]
            self.slots=self.slots[:start]+part+self.slots[start+12:]
        else:
            raise ValueError('Invalid Square-1 axis')

    def apply_moves(self,moves):
        for move in moves:
            self.apply_move(move)

    def validate(self):
        if len(self.slots)!=24 or self.middle not in (0,1) or any(p not in range(16) for p in self.slots):
            raise ValueError('square1.error.incomplete')
        counts=Counter(self.slots)
        if any(counts[p]!=(2 if p&1 else 1) for p in range(16)):
            raise ValueError('square1.error.duplicate')
        for start in (0,12):
            layer=self.slots[start:start+12]
            for i,p in enumerate(layer):
                if p&1 and (layer[(i-1)%12]!=p and layer[(i+1)%12]!=p):
                    raise ValueError('square1.error.split')
        return self

    def scramble(self,length=20,seed=None):
        rng=random.Random(seed)
        for _ in range(length):
            for axis in (0,1):
                candidates=[]
                for amount in range(12):
                    work=self.clone()
                    work.apply_move(Square1Move(axis,amount))
                    if work.can_slice():
                        candidates.append(amount)
                self.apply_move(Square1Move(axis,rng.choice(candidates)))
            self.apply_move(Square1Move(2))
        return self

    def groups(self):
        """(layer, first angular unit, width, piece), including wrapped corners."""
        out=[]
        for layer in (0,1):
            p=self.slots[layer*12:layer*12+12]
            for i,piece in enumerate(p):
                if piece<0 or (piece&1 and p[(i-1)%12]==piece):
                    continue
                out.append((layer,i,2 if piece&1 else 1,piece))
        return tuple(out)

    def solver_shape(self):
        """Shape coordinate only applies when no corner crosses either cut."""
        if not self.can_slice():
            raise ValueError('square1.error.blocked')
        sequence=[]
        for layer in (self.slots[:12],self.slots[12:]):
            sequence.extend(p for i,p in enumerate(layer) if i==0 or p!=layer[i-1])
        parity=sum(a>b for i,a in enumerate(sequence) for b in sequence[i+1:])%2
        bits=0
        for p in self.slots:
            bits=(bits<<1)|(p&1)
        return bits,parity

    def square_coordinates(self):
        corners=tuple(self.slots[a*3+1]>>1 for a in range(8))
        top_first=self.slots[0]==self.slots[1]
        bottom_first=self.slots[12]==self.slots[13]
        edges=tuple(self.slots[(2 if top_first else 0)+a*3]>>1 for a in range(4))
        edges+=tuple(self.slots[(14 if bottom_first else 12)+a*3]>>1 for a in range(4))
        return edges,corners,top_first,bottom_first,self.middle
