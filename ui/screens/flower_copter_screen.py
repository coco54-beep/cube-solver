"""Flower play controls; colour and manual-pose editors stay disabled."""
from functools import partial
from cube.curvy_copter import JUMBLE
from cube.flower_copter_aligned import scrambled,observed_colors
from renderer.flower_copter_view import FlowerCopterView
from ui.screens.pisces_screen import PiscesInputScreen
from ui.screens.copter_screen import CopterTwistScreen


class FlowerCopterInputScreen(PiscesInputScreen):
    view_class=FlowerCopterView
    entry_twist_screen='FlowerCopterTwistScreen'
    make_scrambled=staticmethod(partial(scrambled,shape=True))
    pose_presets=(('90°',90.),('120°',120.),('180°',180.))

    @staticmethod
    def validate_aligned(cube):
        from solver.flower_copter import validate
        validate(observed_colors(cube))


class FlowerCopterTwistScreen(CopterTwistScreen):
    entry_screen_name='FlowerCopterInputScreen'

    def _set_layers(self):
        self._angles=(180.,JUMBLE,180.-JUMBLE) if self._axis<12 else (120.,60.)
        self.layer.values=tuple(f'{a:g}°' for a in self._angles)
        self.layer.disabled=False;self._layer=0
        self.layer.text=self.layer.values[0]
        self._layer_selected(self.layer,self.layer.text)

    def _layer_selected(self,widget,text):
        if text in widget.values:
            self._angle=self._angles[widget.values.index(text)];self.view.turn_amount=self._angle
            if self._axis<12:self.view.edge_amount=self._angle
            else:self.view.corner_amount=self._angle
