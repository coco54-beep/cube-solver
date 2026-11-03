"""Radius-one Butterflower, using the shared colours, seams and animation."""
from functools import lru_cache
from cube import butterflower_material as material
from renderer.flower_copter_view import FlowerCopterView,load_skin_data,outer_surfaces,build_surfaces
from renderer.copter_view import CopterTwistView


@lru_cache(maxsize=1)
def skin_data():return load_skin_data(material,'butterflower_regular_skin.bin')


def surfaces():return skin_data()[0]


class ButterflowerView(FlowerCopterView):
    home_surfaces=staticmethod(surfaces)
    skin=staticmethod(skin_data)
    outer_skin=staticmethod(lambda:outer_surfaces(material))


class ButterflowerTwistView(ButterflowerView,CopterTwistView):
    def amount_for_axis(self,axis):return self.turn_amount if axis<12 else 120.
