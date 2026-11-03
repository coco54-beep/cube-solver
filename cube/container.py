"""Tony Fisher / MoYu Container: a rectangular shell on a Skewb core.

The long axis is sqrt(2) times the two short axes; the shell is rotated 45
degrees relative to the core. Its eight triangular faces on corner pieces,
four oriented rhombi and two square centres must move as rigid pieces.
"""
from functools import lru_cache
import math
from cube.fisher_skewb import FisherSkewbCube,SHELL_NORMALS
from cube.mastermorphix import transform
from cube.mirror_tower import _clip_solid
from cube.polyhedral import geometry,body,dot,scale,key


@lru_cache(maxsize=14)
def piece_faces(home):
    bounds=tuple(math.sqrt(2) if abs(normal[1])>.9 else 1. for normal in SHELL_NORMALS)
    shell=body(tuple(scale(n,1/d) for n,d in zip(SHELL_NORMALS,bounds)))
    polygons=[(tuple(p),face) for face,p in enumerate(shell)]
    g=geometry('skewb',3)
    for axis in g.spec.axes:
        normal=scale(axis,-1 if dot(axis,g.centres[home])>0 else 1)
        polygons=_clip_solid(polygons,normal,0.)
    return tuple(polygons)


@lru_cache(maxsize=256)
def appearance(home,frame):
    return tuple(sorted((colour,tuple(sorted(key(transform(frame,p)) for p in poly)))
                        for poly,colour in piece_faces(home) if colour>=0))


class ContainerCube(FisherSkewbCube):
    puzzle_kind='container'
    appearance=staticmethod(appearance)

    def piece_faces(self,home):return piece_faces(home)
