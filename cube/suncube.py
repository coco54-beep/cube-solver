"""SunCube II: twelve deep edge caps on a cubical material shell.

The depth is half-width times (sqrt(2)-1), independently constructed from
plane intersections. It is not the shallow Clover or Helicopter layout.
"""
from functools import lru_cache
import math
from cube.polyhedral import CUBE,EDGE_AXES,body,scale,Move
from cube.twins_material import partition
from cube.planar_twins_state import PlanarTwinsState as TwinsState
from cube.curvy_copter import JUMBLE

CUT=.5*(math.sqrt(2)-1)


@lru_cache(maxsize=1)
def structure():
    cells=(tuple((tuple(scale(p,.5) for p in poly),f) for f,poly in enumerate(body(CUBE))),)
    for normal in EDGE_AXES:cells=partition(cells,normal,CUT)
    # Enclosed core cells have no visible material and no independent turn.
    cells=tuple(c for c in cells if any(f>=0 for p,f in c))
    panels=tuple((h,f,p) for h,cell in enumerate(cells) for p,f in cell if f>=0)
    return cells,panels


@lru_cache(maxsize=1)
def layout():
    solids,panels=structure();return tuple(range(len(solids))),solids,panels


class SunCube(TwinsState):
    puzzle_kind='mf8_suncube_2'
    layout=staticmethod(layout)
    turn_axes=EDGE_AXES
    cut_bounds=(CUT,)*12
    turn_steps=(180,)*12
    observation_model='mf8-suncube-ii'

    def moves(self):
        return tuple(Move(a,0,angle) for a in range(12)
                     for angle in (180.,JUMBLE,-JUMBLE,180-JUMBLE,JUMBLE-180))
