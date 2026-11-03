"""Silver, unequal Minx solids and their genuine 72-degree turns."""
import math
from cube.mirror_minx import OFFSET
from cube.polyhedral import rotate,scale
from renderer.mirror_tower_view import MirrorTowerView
from renderer.polyhedral_view import PolyhedralTwistView
from renderer.tutorial_markers import TutorialMarkersMixin


class MirrorMinxView(TutorialMarkersMixin,MirrorTowerView):
    shell_scale=1.25
    camera_target=scale(OFFSET,shell_scale)

    def _motion(self,points,normal,slot,layer,start,width):
        if self._move is None or start not in self.cube.geometry.layers[self._move.axis][self._move.layer]:
            return points,normal
        axis=self.cube.geometry.spec.axes[self._move.axis];amount=self._move.amount%5
        if amount>2:amount-=5
        angle=amount*2*math.pi/5*self._fraction
        return tuple(rotate(p,axis,angle) for p in points),rotate(normal,axis,angle)


class MirrorMinxTwistView(MirrorMinxView,PolyhedralTwistView):pass
