"""Stronger relaxed distances for Camouflage's fixed-anchor search."""
from functools import lru_cache
from itertools import combinations
import hashlib


@lru_cache(maxsize=1)
def anchored_model():
    from solver.cuboid_search import search_model
    from cube.cuboid import layout,IDENTITY
    from cube.appearance import ROTATIONS
    atoms,transitions,legal,goals,patterns,aliases=search_model('camouflage_3')
    cells=layout('camouflage_3')[0]
    anchor=max(range(len(cells)),key=lambda p:len(cells[p]))
    pose=aliases[anchor][ROTATIONS.index(IDENTITY)]
    fixed=sum(1<<i for i,dest in enumerate(transitions[anchor][pose]) if dest==pose)
    restricted=tuple(tuple(bytes(dest if fixed>>i&1 else 255 for i,dest in enumerate(row))
                           for row in piece) for piece in transitions)
    masks=tuple(tuple(mask&fixed for mask in row) for row in legal)
    heavy=tuple(p for p,group in enumerate(cells) if len(group)==4)
    # Cover every set of four large pieces. The smaller original projections
    # cover all other pieces, with the now constant anchor coordinate removed.
    projections=tuple(combinations(heavy,4))+tuple(tuple(p for p in group if p!=anchor)
                                                  for group in patterns)
    return atoms,restricted,masks,goals,projections,aliases


@lru_cache(maxsize=1)
def fingerprint():
    return hashlib.sha256(repr(anchored_model()).encode('utf-8')).hexdigest()
