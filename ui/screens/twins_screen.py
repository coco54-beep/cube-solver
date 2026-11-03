"""Twins observation uses the shared paint, draft pose and playback workflow."""
from app.i18n import tr
from functools import partial
from cube.curvy_copter import JUMBLE
from cube.twins_state import SECOND
from cube.twins_pcubes_aligned import scrambled,observed_colors
from renderer.twins_view import TwinsView
from ui.screens.copter_screen import CopterInputScreen,CopterTwistScreen


class TwinsInputScreen(CopterInputScreen):
    view_class=TwinsView
    entry_twist_screen='TwinsTwistScreen'
    make_scrambled=staticmethod(partial(scrambled,jumble=True))
    pose_presets=(('90°',90.),('120°',120.),('180°',180.))

    @staticmethod
    def validate_aligned(cube):
        from solver.twins_pcubes import validate
        if getattr(cube,'geometry_profile',None)!='pcubes-skewby-twins-v1':
            from solver.twins import validate
        validate(observed_colors(cube))

    def _pose_refresh(self):
        self.pose_piece.text=tr('comet.piece',number=self._pose_home+1)
        self.pose_preview.selected_piece=self._pose_home
        self.pose_preview.cube=self._pose_work;self.pose_preview.refresh()

    def confirm_pose(self):
        if self._cube is not self._pose_target:return
        try:self._pose_work=self._pose_work.complete_hidden()
        except ValueError:pass  # Keep an unfinished visible draft editable.
        super().confirm_pose()


class TwinsTwistScreen(CopterTwistScreen):
    entry_screen_name='TwinsInputScreen'
    def _set_layers(self):
        self._angles=(180.,JUMBLE,180.-JUMBLE,SECOND,180.-SECOND) if self._axis<12 else (120.,60.)
        values=tuple(f'{a:g}°' for a in self._angles)
        self.layer.values=values;self.layer.disabled=False;self._layer=0
        self.layer.text=values[0]
        self._layer_selected(self.layer,self.layer.text)

    def _layer_selected(self,widget,text):
        if text in widget.values:
            self._angle=self._angles[widget.values.index(text)];self.view.turn_amount=self._angle
            if self._axis<12:self.view.edge_amount=self._angle
            else:self.view.corner_amount=self._angle


from renderer.twins_view import SunCubeView
from cube.suncube_aligned import scrambled as sun_scrambled


class SunCubeInputScreen(CopterInputScreen):
    view_class=SunCubeView
    entry_twist_screen='SunCubeTwistScreen'
    make_scrambled=staticmethod(sun_scrambled)

    @staticmethod
    def validate_aligned(cube):
        from solver.suncube import validate
        validate(observed_colors(cube))


class SunCubeTwistScreen(CopterTwistScreen):
    entry_screen_name='SunCubeInputScreen'
