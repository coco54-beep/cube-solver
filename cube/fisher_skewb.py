"""Coloured Fisher Skewb: a rigid cube shell at 45 degrees to a Skewb core."""
from functools import lru_cache
import math

from cube.mastermorphix import transform, IDENTITY
from cube.mirror_skewb import MirrorSkewbCube
from cube.mirror_tower import _clip_solid
from cube.polyhedral import CUBE, body, geometry, dot, scale, key

S=math.sqrt(.5)
SHELL_FRAME=((S,0.,-S),(0.,1.,0.),(S,0.,S))
SHELL_NORMALS=tuple(transform(SHELL_FRAME,n) for n in CUBE)


@lru_cache(maxsize=14)
def piece_faces(home):
    g=geometry('skewb',3)
    polygons=[(tuple(p),face) for face,p in enumerate(body(SHELL_NORMALS))]
    for axis in g.spec.axes:
        normal=scale(axis,-1 if dot(axis,g.centres[home])>0 else 1)
        polygons=_clip_solid(polygons,normal,0.)
    return tuple(polygons)


@lru_cache(maxsize=256)
def appearance(home,frame):
    """Visible coloured facets; a square's invisible half-turn is equivalent."""
    return tuple(sorted((colour,tuple(sorted(key(transform(frame,p)) for p in poly)))
                        for poly,colour in piece_faces(home) if colour>=0))


class FisherSkewbCube(MirrorSkewbCube):
    puzzle_kind='fisher_skewb'

    def piece_faces(self,home):
        return piece_faces(home)

    def is_solved(self):
        return (len(self.pieces)==len(self.geometry.pieces) and all(
            appearance(piece.home,piece.frame)==appearance(position,IDENTITY)
            for position,piece in self.pieces.items()))
