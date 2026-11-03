"""Private finite colour action after the research Copter has regained shape.

Virtual generators are complete, guarded physical words. They are never
exposed as fictitious turn axes in the catalogue or user interface.
"""
from functools import lru_cache
from itertools import combinations,product
import hashlib
from cube.polyhedral import (Geometry,Spec,Sticker,Move,CUBE,EDGE_AXES,dot,
                            mean)
from cube.curvy_copter import CopterState,JUMBLE,cuts


def inverse_word(word):return tuple(Move(m.axis,0,-m.amount) for m in reversed(word))


@lru_cache(maxsize=1)
def source_key():
    return hashlib.sha256(repr((CopterState().signatures,cuts())).encode('ascii')).hexdigest()


def compact(word):
    result=[]
    for m in word:
        amount=(m.amount+180.)%360.-180.
        if abs(amount)<1e-7:continue
        if result and result[-1].axis==m.axis:
            old=result.pop();amount=(old.amount+amount+180.)%360.-180.
        if abs(amount)>1e-7:result.append(Move(m.axis,0,amount))
    return tuple(result)


@lru_cache(maxsize=1)
def generators():
    base=CopterState();found={}
    words=[(Move(axis,0,180.),) for axis in range(12)]
    # Disjoint preparation caps at opposite ends of a target edge. Determine
    # the working signs by actual whole-region clearance, not a preset table.
    for target,normal in enumerate(EDGE_AXES):
        neighbours=[i for i,n in enumerate(EDGE_AXES) if abs(dot(n,normal)-.5)<1e-8]
        for a,b in combinations(neighbours,2):
            if dot(EDGE_AXES[a],EDGE_AXES[b])>-.49:continue
            for sa,sb in product((-1,1),repeat=2):
                words.append((Move(a,0,sa*JUMBLE),Move(b,0,sb*JUMBLE),Move(target,0,180.),
                              Move(b,0,-sb*JUMBLE),Move(a,0,-sa*JUMBLE)))
    for word in words:
        work=base.clone()
        try:
            for m in word:work.apply_move(m)
            action=work.aligned_permutation()
        except ValueError:continue
        if any(action[action[s]]!=s for s in range(72)):
            raise ValueError('Closed Copter generator is not an involution')
        if action not in found or len(word)<len(found[action]):found[action]=word
    return tuple((action,word) for action,word in found.items())


@lru_cache(maxsize=1)
def geometry():
    state=CopterState();panels=state.panels
    visible=tuple(sorted({home for home,face,p in panels}));owners={h:i for i,h in enumerate(visible)}
    stickers=tuple(Sticker(owners[h],face,p) for h,face,p in panels)
    pieces=tuple(tuple(i for i,s in enumerate(stickers) if s.piece==p) for p in range(len(visible)))
    centres=tuple(mean(tuple(c.centre for i,c in enumerate(cuts()) if state.signatures[h]&(1<<i))) for h in visible)
    rows=generators();actions=tuple((action,) for action,word in rows)
    layers=tuple((tuple(p for p,slots in enumerate(pieces) if any(action[s]!=s for s in slots)),) for action,word in rows)
    # Only abstract involutions are used by the finite group builder. Normals
    # and outlines retain actual geometry for identity and asset fingerprints.
    axes=tuple(EDGE_AXES[word[len(word)//2].axis] for action,word in rows)
    return Geometry(Spec('_copter_aligned',3,CUBE,axes,(),2),stickers,pieces,centres,actions,layers)


class AlignedCopter:
    puzzle_kind='_copter_aligned'
    n=3
    color_count=6
    def __init__(self,colors=None):
        self.geometry=geometry()
        self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=len(self.geometry.stickers):raise ValueError('Wrong Copter panel count')
    def clone(self):return type(self)(self.colors)
    entered=clone
    def moves(self):return tuple(Move(i) for i in range(len(generators())))
    def apply_move(self,move):
        inverse=self.geometry.inverse_permutation(move)
        self.colors=[self.colors[i] for i in inverse];return self
    def is_solved(self):return self.colors==[s.face for s in self.geometry.stickers]


def observed_colors(cube):
    result=[None]*len(cube.panels)
    for source,destination in enumerate(cube.aligned_permutation()):result[destination]=cube.paints[source]
    return tuple(result)


def expand(word):
    return compact(tuple(atom for move in word if move.amount%2 for atom in generators()[move.axis][1]))
