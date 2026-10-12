"""Editable Square-1 block shapes and painted colours, independent of IDs."""
from dataclasses import dataclass
from cube.square1 import Square1Cube,piece_colors


@dataclass(frozen=True)
class EntryBlock:
    width:int
    colors:tuple


class Square1Entry:
    color_entry=True
    puzzle_kind='square1'
    n=3

    def __init__(self,cube=None,colored=False):
        cube=cube or Square1Cube()
        self.middle=cube.middle
        self.slots=[-1]*24
        self.blocks={}
        for layer,start,width,piece in cube.groups():
            identity=layer*12+start
            colors=piece_colors(piece)
            self.blocks[identity]=EntryBlock(width,(colors[0],)+colors[1] if colored else (-2,)*(width+1))
            for offset in range(width):
                self.slots[layer*12+(start+offset)%12]=identity

    def clone(self):
        result=object.__new__(type(self))
        result.slots=list(self.slots)
        result.blocks=dict(self.blocks)
        result.middle=self.middle
        return result

    def groups(self):
        return tuple((layer,i,self.blocks[piece].width,piece)
                     for layer in (0,1) for i,piece in enumerate(self.slots[layer*12:layer*12+12])
                     if piece>=0 and self.slots[layer*12+(i-1)%12]!=piece)

    def block_start(self,slot):
        piece=self.slots[slot]
        if piece<0:
            return slot
        return next(layer*12+start for layer,start,width,p in self.groups() if p==piece)

    def piece_colors(self,piece):
        colors=self.blocks[piece].colors
        return colors[0],colors[1:]

    def set_shape(self,slot,width):
        slot=self.block_start(slot)
        old=self.slots[slot]
        if old>=0 and self.blocks[old].width==width:
            return slot
        targets=[slot//12*12+(slot%12+i)%12 for i in range(width)]
        displaced={self.slots[i] for i in targets}-{ -1 }
        identity=max(self.blocks,default=-1)+1
        self.slots=[-1 if p in displaced else p for p in self.slots]
        for p in displaced:
            self.blocks.pop(p)
        self.blocks[identity]=EntryBlock(width,(-2,)*(width+1))
        for i in targets:
            self.slots[i]=identity
        return slot

    def paint(self,slot,field,color):
        identity=self.slots[slot]
        block=self.blocks[identity]
        colors=list(block.colors)
        colors[field]=color
        self.blocks[identity]=EntryBlock(block.width,tuple(colors))

    def rotate_layer(self,layer,amount):
        start=layer*12
        ring=self.slots[start:start+12]
        amount%=12
        self.slots[start:start+12]=ring[amount:]+ring[:amount]

    def complete_count(self):
        return sum(all(c>=0 for c in block.colors) for block in self.blocks.values())

    def to_cube(self):
        if -1 in self.slots or len(self.blocks)!=16 or self.complete_count()!=16:
            raise ValueError('square1.error.incomplete')
        reference={(1+(piece&1),(cap,)+sides):piece
                   for piece in range(16) for cap,sides in (piece_colors(piece),)}
        identities={}
        for identity,block in self.blocks.items():
            try:
                identities[identity]=reference[(block.width,block.colors)]
            except KeyError:
                raise ValueError('square1.error.colors') from None
        if len(set(identities.values()))!=16:
            raise ValueError('square1.error.duplicate')
        return Square1Cube(tuple(identities[p] for p in self.slots),self.middle).validate()
