"""Offset-cut mirror cubes with oriented piece geometry and virtual labels."""
from functools import lru_cache
from itertools import product

from cube.coordinates import coord_values
from cube.mastermorphix import (MastermorphixCube,IDENTITY,ROTATIONS,make_piece,
                               positions_for_order,transform)

OFFSETS=(.28,.12,-.37)


@lru_cache(maxsize=1024)
def piece_faces(home,n):
    values=coord_values(n)
    bounds=[]
    for axis,p in enumerate(home):
        i=values.index(p)
        lo=-n/2+i+(OFFSETS[axis] if i==0 else 0)
        hi=-n/2+i+1+(OFFSETS[axis] if i==n-1 else 0)
        bounds.append((lo,hi))
    faces=[]
    for axis in range(3):
        others=[i for i in range(3) if i!=axis]
        for side in (0,1):
            points=[]
            for a,b in ((0,0),(1,0),(1,1),(0,1)):
                p=[0.,0.,0.]
                p[axis]=bounds[axis][side]
                p[others[0]]=bounds[others[0]][a]
                p[others[1]]=bounds[others[1]][b]
                points.append(tuple(p))
            normal=tuple((1 if side else -1) if i==axis else 0 for i in range(3))
            exterior=values.index(home[axis])==(n-1 if side else 0)
            faces.append((tuple(points),normal,exterior))
    return tuple(faces)


def shape_signature(cube,frame=IDENTITY):
    return tuple(sorted(tuple(sorted(tuple(round(x,6) for x in transform(frame,
                          transform(piece.frame,p))) for p in points))
                        for piece in cube.cubies.values()
                        for points,normal,exterior in piece_faces(piece.home,cube.n) if exterior))


class MirrorCube(MastermorphixCube):
    puzzle_kind='mirror'

    def __init__(self,cubies,palette=('MIRROR',),n=3):
        # Reuse the cube's exact move/frame logic; mirror input never uses
        # the four-color tetrahedral constructor or its shape mapping.
        if not 2<=n<=9:
            raise ValueError('Mirror orders must be between 2 and 9')
        self.cubies=cubies
        self.n=self.size=n
        self.positions=positions_for_order(n)
        self.palette=('MIRROR',)

    @classmethod
    def solved(cls,palette=('MIRROR',),n=3):
        return cls({p:make_piece(p,p,IDENTITY,n) for p in positions_for_order(n)},n=n)

    def is_solved(self):
        if set(self.cubies)!=set(self.positions):
            return False
        signature=shape_signature(self)
        solved=type(self).solved(n=self.n)
        return any(signature==shape_signature(solved,frame) for frame in ROTATIONS)
