"""Piece-card input preserves SQ widths, profiles and layer-pair membership."""
from dataclasses import dataclass

from cube.square_family import SquareFamilyCube, SquarePiece, catalogue, outline, layer_direction


@dataclass(frozen=True)
class SquareFamilyBlock:
    home: int
    confirmed: bool = False


class SquareFamilyEntry:
    color_entry = True
    n = 3

    @property
    def layer_count(self):
        return 4 if self.puzzle_kind == 'super_square1' else 2

    @property
    def specs(self):
        return catalogue(self.puzzle_kind)[1]

    def __init__(self, cube=None, colored=False, empty=False):
        cube = cube or SquareFamilyCube()
        self.puzzle_kind = cube.puzzle_kind
        self.middle = cube.middle
        self.slots = [-1]*len(cube.slots)
        self.blocks = {}
        if empty:
            return
        for layer,start,width,home in cube.groups():
            identity = layer*12+start
            self.blocks[identity] = SquareFamilyBlock(home,colored)
            for i in range(width):
                self.slots[layer*12+(start+i)%12] = identity

    def clone(self):
        result = object.__new__(type(self))
        result.__dict__.update(self.__dict__)
        result.slots = list(self.slots)
        result.blocks = dict(self.blocks)
        return result

    def layer_direction(self,layer):
        return layer_direction(layer,self.layer_count)

    def groups(self):
        return tuple((layer,i,self.specs[self.blocks[p].home].width,p)
                     for layer in range(self.layer_count)
                     for i,p in enumerate(self.slots[layer*12:layer*12+12])
                     if p >= 0 and self.slots[layer*12+(i-1)%12] != p)

    def block_start(self,slot):
        identity = self.slots[slot]
        return (next(layer*12+start for layer,start,_,p in self.groups() if p == identity)
                if identity >= 0 else slot)

    def piece_colors(self,piece):
        block = self.blocks[piece]
        colors = self.specs[block.home].colors
        if not block.confirmed:
            colors = tuple(-1 if c == -1 else -2 for c in colors)
        return colors[0],colors[1:]

    def outline(self,layer,start,width,piece):
        spec = (self.specs[self.blocks[piece].home] if piece >= 0 else
                SquarePiece(1,((0.,1.03527618041),(1.,1.03527618041)),()))
        return outline(spec,layer,start,self.layer_count)

    def choose_piece(self,slot,home):
        slot = self.block_start(slot)
        from cube.ring_entry import placement
        if not 0 <= home < len(self.specs):
            raise ValueError('sq.error.move')
        width = self.specs[home].width
        if self.layer_count == 4 and self.specs[home].pair != int(slot//12 in (1,2)):
            raise ValueError('sq.error.move')
        if any(b.home == home for p,b in self.blocks.items() if p != self.slots[slot] and b.confirmed):
            raise ValueError('square1.error.duplicate')
        targets,old = placement(self.slots,slot,width)
        displaced = {old}-{-1}
        self.slots = [-1 if p in displaced else p for p in self.slots]
        for p in displaced:
            self.blocks.pop(p)
        identity = max(self.blocks,default=-1)+1
        self.blocks[identity] = SquareFamilyBlock(home,True)
        for i in targets:
            self.slots[i] = identity
        return slot

    def rotate_layer(self,layer,amount):
        start = layer*12
        ring = self.slots[start:start+12]
        amount %= 12
        self.slots[start:start+12] = ring[amount:]+ring[:amount]

    def can_slice(self):
        return -1 not in self.slots and all(self.slots[layer*12+a] != self.slots[layer*12+b]
                                          for layer in range(self.layer_count) for a,b in ((11,0),(5,6)))

    def apply_move(self,move):
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
            self.slots = slots
            self.middle ^= 1
        elif 0 <= move.axis < self.layer_count:
            if self.puzzle_kind == 'square0' and move.amount % 3:
                raise ValueError('sq.error.quarter')
            self.rotate_layer(move.axis,move.amount)
        else:
            raise ValueError('sq.error.move')

    def complete_count(self):
        return sum(block.confirmed for block in self.blocks.values())

    def to_cube(self):
        if -1 in self.slots or len(self.blocks) != len(self.specs) or self.complete_count() != len(self.specs):
            raise ValueError('sq.error.incomplete')
        homes = [block.home for block in self.blocks.values()]
        if len(set(homes)) != len(self.specs):
            raise ValueError('square1.error.duplicate')
        cube = SquareFamilyCube(self.puzzle_kind,tuple(self.blocks[p].home for p in self.slots),self.middle)
        return cube.validate()
