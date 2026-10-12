"""Mirror Jing's Pyraminx: rigid asymmetric pieces with oriented centres.

The input records home pieces and tetrahedral frames. Solver markers retain
the orientation of silver centres, which a face-colour state would discard.
"""
from dataclasses import dataclass
from functools import lru_cache
import math

from cube.polyhedral import geometry,TETRA,body,clip,dot,cross,unit,mean,add,scale,key,rotate,Move,Sticker,Geometry
from cube.mastermorphix import IDENTITY,transform


# Shift a regular tetrahedral housing relative to its turning core. This
# changes piece widths without changing the tetrahedron's edge lengths or
# the Jing mechanism. Front-face cuts now have visibly unequal spacing.
SHELL_OFFSET=(-.34,-.61,.08)

def frame_key(frame):
    return tuple(key(v) for v in frame)


def multiply(a,b):
    return tuple(transform(a,v) for v in b)


def transpose(frame):
    return tuple(tuple(frame[i][j] for i in range(3)) for j in range(3))


@lru_cache(maxsize=1)
def frames():
    found=[IDENTITY]
    seen={frame_key(IDENTITY)}
    for frame in found:
        for axis in TETRA:
            nxt=tuple(rotate(v,axis,2*math.pi/3) for v in frame)
            if frame_key(nxt) not in seen:
                seen.add(frame_key(nxt))
                found.append(nxt)
    return tuple(found)


@lru_cache(maxsize=196)
def placements(home,position):
    g=geometry('moyu',3)
    return tuple(f for f in frames() if sum((a-b)**2 for a,b in
                 zip(transform(f,g.centres[home]),g.centres[position]))<1e-10)


def _clip_solid(polygons,normal,bound):
    result=[]
    seam={}
    for points,color in polygons:
        kept=clip(points,normal,bound)
        if kept:
            result.append((kept,color))
            for p in kept:
                if abs(dot(normal,p)-bound)<1e-7:
                    seam[key(p)]=p
    if len(seam)>=3:
        centre=mean(tuple(seam.values()))
        u=unit(add(next(iter(seam.values())),scale(centre,-1)))
        v=cross(normal,u)
        # Facet intersections also contain points inside the cap. Sorting all
        # of them around the centre creates a zigzag instead of a closed face.
        planar=sorted((dot(p,u),dot(p,v),p) for p in seam.values())
        def side(a,b,c):
            return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        def hull(values):
            result=[]
            for point in values:
                while len(result)>=2 and side(result[-2],result[-1],point)<=1e-10:
                    result.pop()
                result.append(point)
            return result
        cap=[p[2] for p in hull(planar)[:-1]+hull(planar[::-1])[:-1]]
        result.append((tuple(cap),-1))
    return result


@lru_cache(maxsize=14)
def piece_faces(home):
    # An offset outer shell gives every mirror piece different dimensions;
    # the four intersecting mechanical cut planes still pass through the core.
    polys=[(tuple(add(p,SHELL_OFFSET) for p in face),0) for face in flat_shell()]
    centre=geometry('moyu',3).centres[home]
    for axis in TETRA:
        normal=scale(axis,-1 if dot(axis,centre)>0 else 1)
        polys=_clip_solid(polys,normal,0.)
    return tuple(polys)


@lru_cache(maxsize=1)
def flat_shell():
    """Four planar equilateral faces; no spherical tetrahedral projection."""
    return body(TETRA)


@dataclass(frozen=True)
class Piece:
    home:int
    frame:tuple=IDENTITY


@lru_cache(maxsize=1)
def marker_system():
    g=geometry('moyu',3)
    representatives=tuple(next(i for i,p in enumerate(g.pieces) if len(p)==length) for length in (3,2,1))
    points=[]
    for orbit,base in enumerate(representatives):
        for frame in frames():
            p=transform(frame,g.centres[base])
            position=min(range(len(g.pieces)),key=lambda i:sum((a-b)**2 for a,b in zip(g.centres[i],p)))
            points.append((orbit,position,frame))
    index={(o,frame_key(f)):i for i,(o,p,f) in enumerate(points)}
    permutations=[]
    for axis,layers in enumerate(g.layers):
        turn=tuple(rotate(v,g.spec.axes[axis],2*math.pi/3) for v in IDENTITY)
        permutations.append(tuple(tuple(index[(o,frame_key(multiply(turn,f)))] if p in layer else i
                                         for i,(o,p,f) in enumerate(points)) for layer in layers))
    markers=tuple(Sticker(p,i,()) for i,(o,p,f) in enumerate(points))
    pieces=tuple(tuple(i for i,(_,p,_) in enumerate(points) if p==position) for position in range(len(g.pieces)))
    virtual=Geometry(g.spec,markers,pieces,g.centres,tuple(permutations),g.layers)
    return tuple(points),index,virtual


class MirrorTowerCube:
    puzzle_kind='mirror_tower'
    n=3

    def __init__(self,pieces=None):
        self.geometry=geometry('moyu',3)
        self.pieces=dict(pieces) if pieces is not None else {i:Piece(i) for i in range(len(self.geometry.pieces))}

    @classmethod
    def solved(cls):
        return cls()

    def clone(self):
        return type(self)(self.pieces)

    entered=clone

    def moves(self):
        return tuple(Move(a,l) for a,layers in enumerate(self.geometry.layers) for l in range(len(layers)))

    def apply_move(self,move):
        g=self.geometry
        angle=2*math.pi*(move.amount%3)/3
        turn=tuple(rotate(v,g.spec.axes[move.axis],angle) for v in IDENTITY)
        result=dict(self.pieces)
        for pos in g.layers[move.axis][move.layer]:
            p=self.pieces[pos]
            centre=transform(turn,g.centres[pos])
            target=min(range(len(g.centres)),key=lambda i:sum((a-b)**2 for a,b in zip(g.centres[i],centre)))
            result[target]=Piece(p.home,multiply(turn,p.frame))
        self.pieces=result
        return self

    def labeled_state(self):
        points,index,_=marker_system()
        if set(self.pieces)!=set(range(len(self.geometry.pieces))):
            raise ValueError('Incomplete mirror piece state')
        by_home={piece.home:piece for piece in self.pieces.values()}
        if set(by_home)!=set(range(len(self.geometry.pieces))):
            raise ValueError('Duplicate mirror piece')
        for pos,piece in self.pieces.items():
            if not any(frame_key(piece.frame)==frame_key(frame) for frame in placements(piece.home,pos)):
                raise ValueError('Impossible mirror piece orientation')
        result=[]
        for orbit,home,frame in points:
            result.append(index[(orbit,frame_key(multiply(by_home[home].frame,frame)))])
        return tuple(result)

    @property
    def colors(self):
        state=self.labeled_state()
        inverse=[0]*len(state)
        for source,dest in enumerate(state):
            inverse[dest]=source
        return inverse

    @colors.setter
    def colors(self,values):
        points,_,_=marker_system()
        if sorted(values)!=list(range(len(points))):
            raise ValueError('Incomplete mirror piece state')
        state=[0]*len(values)
        for dest,source in enumerate(values):
            state[source]=dest
        result={}
        homes=set()
        for source,(_,home,frame) in enumerate(points):
            if home in homes:
                continue
            orbit,position,target_frame=points[state[source]]
            if orbit!=points[source][0] or position in result:
                raise ValueError('Invalid mirror piece state')
            result[position]=Piece(home,multiply(target_frame,transpose(frame)))
            homes.add(home)
        restored=type(self)(result)
        if restored.labeled_state()!=tuple(state):
            raise ValueError('Inconsistent mirror piece orientation')
        self.pieces=result

    def is_solved(self):
        return all(p.home==pos and frame_key(p.frame)==frame_key(IDENTITY) for pos,p in self.pieces.items()) and len(self.pieces)==14


def solve_mirror_tower(cube,cancel=None,progress=None):
    from solver.polyhedral import StabilizerChain,simplify
    if cube.is_solved():
        return ()
    points,index,virtual=marker_system()
    class Markers:
        geometry=virtual
        def moves(self):
            return cube.moves()
    chain=StabilizerChain(Markers(),cancel,progress)
    word=chain.solve(cube.labeled_state())
    solution=simplify(word.flatten(3,cancel),3)
    replay=cube.clone()
    for move in solution:
        if cancel and cancel():
            raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError('Mirror tower solution did not restore its shape')
    return solution
