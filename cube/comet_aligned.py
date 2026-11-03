"""Finite, closed-shape actions, expanded to real guarded Comet turns."""
from functools import lru_cache
import hashlib
from cube.polyhedral import Spec,Geometry,Sticker,Move,EDGE_AXES,mean
from cube.crazy_comet import CometCube,generators,structure,CUT


@lru_cache(maxsize=1)
def source_key():
    return hashlib.sha256(repr((CUT,structure())).encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def geometry():
    base=CometCube();pieces=tuple(tuple(i for i,(h,f,p) in enumerate(base.panels) if h==home)
                                  for home in range(len(base.solids)))
    rows=generators();stickers=tuple(Sticker(h,f,p) for h,f,p in base.panels)
    centres=base.geometry.centres
    layers=tuple((tuple(p for p,slots in enumerate(pieces) if any(action[i]!=i for i in slots)),)
                 for action,word in rows)
    axes=tuple(EDGE_AXES[word[len(word)//2].axis] for action,word in rows)
    return Geometry(Spec('_comet_aligned',3,EDGE_AXES,axes,(),2),stickers,pieces,centres,
                    tuple((action,) for action,word in rows),layers)


class AlignedComet:
    puzzle_kind='_comet_aligned'
    n=3
    color_count=12
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
