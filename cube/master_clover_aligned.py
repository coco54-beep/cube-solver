"""Finite closed double-layer action, independently of scramble history."""
from functools import lru_cache
from random import Random
from cube.master_clover import MasterCloverCube,source_key
from cube.polyhedral import Move,Spec,Geometry,CUBE,EDGE_AXES
from cube.crazy_comet import observed_colors


@lru_cache(maxsize=1)
def generators():
    root=MasterCloverCube();rows=[]
    for move in root.moves():rows.append((root.clone().apply_move(move).aligned_permutation(),(move,)))
    return tuple(rows)


@lru_cache(maxsize=1)
def geometry():
    g=MasterCloverCube().geometry;rows=generators()
    return Geometry(Spec('_master_clover_aligned',3,CUBE,tuple(EDGE_AXES[w[0].axis] for a,w in rows),(),2),
                    g.stickers,g.pieces,g.centres,tuple((a,) for a,w in rows),
                    tuple((tuple(h for h,ids in enumerate(g.pieces) if any(a[s]!=s for s in ids)),) for a,w in rows))


class AlignedMasterClover:
    puzzle_kind='_master_clover_aligned'
    n=3
    color_count=6
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=120:raise ValueError('rigid.invalid')
    def clone(self):return type(self)(self.colors)
    entered=clone
    def moves(self):return tuple(Move(i) for i in range(24))
    def apply_move(self,move):
        self.colors=[self.colors[i] for i in self.geometry.inverse_permutation(move)];return self
    def is_solved(self):return self.colors==[s.face for s in self.geometry.stickers]


def expand(word):
    return tuple(atom for move in word if move.amount%2 for atom in generators()[move.axis][1])


@lru_cache(maxsize=1)
def leaf_tool():
    rows=generators();g=geometry()
    for i,(a,aw) in enumerate(rows):
        for j,(b,bw) in enumerate(rows):
            p=tuple(b[a[b[a[s]]]] for s in range(120));changed=tuple(s for s in range(120) if p[s]!=s)
            if len(changed)==3 and all(len(g.pieces[g.stickers[s].piece])==1 for s in changed):
                return (Move(i),Move(j),Move(i),Move(j)),changed
    # Prefer a short certified stabilizer tool when two primitive layers
    # alone do not isolate a single three-cycle.
    from solver.master_clover import _profile
    options=[]
    for row in _profile.data()['transversals']:
        for record in row.values():
            changed=tuple(s for s,p in enumerate(record['permutation']) if s!=p)
            if len(changed)==3 and all(len(g.pieces[g.stickers[s].piece])==1 for s in changed):
                options.append((tuple(Move(*m) for m in record['word']),changed))
    if not options:raise ValueError('No isolated Master Clover wing tool')
    return min(options,key=lambda row:len(row[0]))


def scrambled(seed=None,length=30,cancel=None):
    rng=Random(seed);cube=MasterCloverCube();previous=None
    for _ in range(length):
        if cancel and cancel():raise InterruptedError()
        move=rng.choice([m for m in cube.moves() if (m.axis,m.layer)!=previous]);cube.apply_move(move)
        previous=move.axis,move.layer
    return cube
