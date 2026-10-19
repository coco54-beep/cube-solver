"""Fourteen rigid Ghost Pyramid pieces and a separate alignment phase.

Skewb turns act on aligned mechanical positions; the housing closes only
after an additional partial turn. Shell proportions are an idealised model.
"""
from dataclasses import dataclass
from functools import lru_cache
import math

from cube.mastermorphix import IDENTITY, transform
from cube.mirror_skewb import MirrorSkewbCube
from cube.mirror_tower import _clip_solid, frame_key
from cube.polyhedral import TETRA, add, body, dot, geometry, rotate, scale


ALIGN_AXIS=0
CLOSED_PHASE=60.
SHELL_OFFSET=(.12,-.09,.07)


@lru_cache(maxsize=1)
def shell_frame():
    frame=IDENTITY
    for axis,angle in (((1.,0.,0.),9.),((0.,0.,1.),13.)):
        frame=tuple(rotate(v,axis,math.radians(angle)) for v in frame)
    return frame


def shell_normals():
    return tuple(transform(shell_frame(),n) for n in TETRA)


@dataclass(frozen=True)
class PyramidAlignment:
    angle: float
    axis: int=ALIGN_AXIS
    layer: int=0

    @property
    def amount(self): return self.angle/120.

    def inverse(self,order=3): return PyramidAlignment(-self.angle)


@lru_cache(maxsize=14)
def piece_faces(home):
    g=geometry('skewb',3)
    polygons=[(tuple(add(transform(shell_frame(),p),SHELL_OFFSET) for p in poly),0)
              for poly in body(TETRA)]
    axis=g.spec.axes[ALIGN_AXIS]
    selected=home in g.layers[ALIGN_AXIS][0]
    # Clip the alignment plane before unclosing that half. The remaining
    # mechanical cuts are then made in the aligned mechanism coordinates.
    polygons=_clip_solid(polygons,scale(axis,-1 if selected else 1),0.)
    if selected:
        polygons=[(tuple(rotate(p,axis,math.radians(-CLOSED_PHASE)) for p in poly),c)
                  for poly,c in polygons]
    for i,axis in enumerate(g.spec.axes):
        if i==ALIGN_AXIS: continue
        polygons=_clip_solid(polygons,scale(axis,-1 if dot(axis,g.centres[home])>0 else 1),0.)
    return tuple(polygons)


class GhostPyramidCube(MirrorSkewbCube):
    puzzle_kind='ghost_pyramid'

    def __init__(self,pieces=None,n=3,phase=CLOSED_PHASE):
        super().__init__(pieces,n)
        if not math.isfinite(phase) or not -180<=phase<=180:
            raise ValueError('Invalid Ghost Pyramid alignment')
        self.phase=float(phase)

    def clone(self): return type(self)(self.pieces,self.n,self.phase)
    entered=clone

    def piece_faces(self,home): return piece_faces(home)

    def can_apply(self,move):
        if isinstance(move,PyramidAlignment):
            return (move.axis==ALIGN_AXIS and move.layer==0 and math.isfinite(move.angle)
                    and -180<=self.phase+move.angle<=180)
        return abs(self.phase)<1e-8

    def apply_move(self,move):
        if not self.can_apply(move):
            raise ValueError('ghost_pyramid.align_first')
        if isinstance(move,PyramidAlignment):
            self.phase=round(self.phase+move.angle,8)
            return self
        return super().apply_move(move)

    def alignment_move(self,close=False):
        return PyramidAlignment((CLOSED_PHASE if close else 0.)-self.phase)

    def is_solved(self):
        return (abs(self.phase-CLOSED_PHASE)<1e-8
                and len(self.pieces)==len(self.geometry.pieces)
                and all(piece.home==position and frame_key(piece.frame)==frame_key(IDENTITY)
                        for position,piece in self.pieces.items()))

    @property
    def colors(self):
        # The shared playback checkpoints must retain the alignment as well
        # as virtual orientation markers. This is internal state, not paint.
        return super().colors+[self.phase]

    @colors.setter
    def colors(self,values):
        values=list(values)
        phase=float(values.pop())
        if not math.isfinite(phase) or not -180<=phase<=180:
            raise ValueError('Invalid Ghost Pyramid alignment')
        MirrorSkewbCube.colors.fset(self,values)
        self.phase=phase
