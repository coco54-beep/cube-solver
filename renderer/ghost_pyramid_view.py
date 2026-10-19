"""Rigid silver Ghost Pyramid, including its opening and closing motion."""
import math
from cube.ghost_pyramid import ALIGN_AXIS, PyramidAlignment, SHELL_OFFSET
from cube.polyhedral import rotate, scale
from renderer.mirror_tower_view import MirrorTowerView
from renderer.polyhedral_view import PolyhedralTwistView


class GhostPyramidView(MirrorTowerView):
    camera_target=scale(SHELL_OFFSET,.64)

    @staticmethod
    def _surfaces(cube):
        surfaces=MirrorTowerView._surfaces(cube)
        if abs(cube.phase)<1e-8: return surfaces
        axis=cube.geometry.spec.axes[ALIGN_AXIS]
        selected=cube.geometry.layers[ALIGN_AXIS][0]
        result=[]
        for points,normal,color,slot,layer,pos,width in surfaces:
            if pos in selected:
                angle=math.radians(cube.phase)
                points=tuple(rotate(p,axis,angle) for p in points)
                normal=rotate(normal,axis,angle)
            result.append((points,normal,color,slot,layer,pos,width))
        return tuple(result)

    def _motion(self,points,normal,slot,layer,start,width):
        if isinstance(self._move,PyramidAlignment):
            if start not in self.cube.geometry.layers[ALIGN_AXIS][0]: return points,normal
            axis=self.cube.geometry.spec.axes[ALIGN_AXIS]
            angle=math.radians(self._move.angle)*self._fraction
            return tuple(rotate(p,axis,angle) for p in points),rotate(normal,axis,angle)
        return super()._motion(points,normal,slot,layer,start,width)

    def animate_move(self,move,on_done=None,duration=.3):
        if not self.cube.can_apply(move): return False
        return super().animate_move(move,on_done,duration)

    def reset_camera(self):
        super().reset_camera()
        self.yaw=45
        self.pitch=math.degrees(math.atan(1/math.sqrt(2)))
        self.refresh()


class GhostPyramidTwistView(GhostPyramidView,PolyhedralTwistView):
    pass
