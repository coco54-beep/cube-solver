"""Two-action Butterflower on the existing shared material entry controls."""
from ui.screens.flower_copter_screen import FlowerCopterInputScreen,FlowerCopterTwistScreen
from renderer.butterflower_view import ButterflowerView
from cube.butterflower_aligned import scrambled,observed_colors
from cube.butterflower import JUMBLE
from ui.screens.copter_screen import CopterTwistScreen


class ButterflowerInputScreen(FlowerCopterInputScreen):
    view_class=ButterflowerView
    entry_twist_screen='ButterflowerTwistScreen'
    make_scrambled=staticmethod(scrambled)
    pose_presets=(('J = 70.529°',JUMBLE),('109.471°',180.-JUMBLE),('120°',120.),('180°',180.))

    @staticmethod
    def validate_aligned(cube):
        from solver.butterflower import validate
        validate(observed_colors(cube))


class ButterflowerTwistScreen(FlowerCopterTwistScreen):
    entry_screen_name='ButterflowerInputScreen'

    def _set_layers(self):
        if self._axis<12:CopterTwistScreen._set_layers(self)
        else:super()._set_layers()

    def _layer_selected(self,widget,text):
        if self._axis<12:CopterTwistScreen._layer_selected(self,widget,text)
        else:super()._layer_selected(widget,text)
