"""Coloured solid Fisher Skewb, sharing rigid shape and turn rendering."""
from renderer.mirror_tower_view import MirrorTowerView
from renderer.square1_view import Square1View
from renderer.polyhedral_view import PolyhedralTwistView


class FisherSkewbView(MirrorTowerView):
    camera_target=(0.,0.,0.)

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.yaw=77

    def reset_camera(self):
        if hasattr(self,'lock_view'):
            PolyhedralTwistView.reset_camera(self)
        else:
            Square1View.reset_camera(self)
        self.yaw=77
        self.refresh()

    def set_cube(self,cube):
        Square1View.set_cube(self,cube)

    def _surface_shade(self,normal,eye,light,rgba,color,recorded):
        return Square1View._surface_shade(self,normal,eye,light,rgba,color,recorded)


class FisherSkewbTwistView(FisherSkewbView,PolyhedralTwistView):
    pass
