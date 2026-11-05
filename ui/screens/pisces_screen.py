"""Pisces uses the same paint, pose draft, undo and playback controls."""
from app.i18n import tr
from cube.pisces import ANGLE1,ANGLE2
from cube.pisces_aligned import scrambled,observed_colors
from renderer.pisces_view import PiscesView
from ui.screens.copter_screen import CopterInputScreen,CopterTwistScreen


class PiscesInputScreen(CopterInputScreen):
    view_class=PiscesView
    entry_twist_screen='PiscesTwistScreen'
    make_scrambled=staticmethod(scrambled)
    pose_presets=(('67.115°',ANGLE1),('146.443°',ANGLE2),('90°',90.),('180°',180.))

    @staticmethod
    def validate_aligned(cube):
        from solver.pisces import validate
        validate(observed_colors(cube))

    def _pose_refresh(self):
        self.pose_piece.text=tr('comet.piece',number=self._pose_home+1)
        self.pose_preview.selected_piece=self._pose_home
        self.pose_preview.cube=self._pose_work;self.pose_preview.refresh()


class PiscesTwistScreen(CopterTwistScreen):
    entry_screen_name='PiscesInputScreen'

    def _set_layers(self):
        self.layer.values=('67.115°','146.443°');self.layer.disabled=False;self._layer=0
        if self.layer.text not in self.layer.values:self.layer.text=self.layer.values[0]
        self._layer_selected(self.layer,self.layer.text)

    def _layer_selected(self,widget,text):
        if text in widget.values:
            self._angle=(ANGLE1,ANGLE2)[widget.values.index(text)]
            self.view.turn_amount=self._angle


from renderer.pisces_view import HexagramView
from cube.hexagram_aligned import scrambled as hexagram_scrambled


class HexagramInputScreen(PiscesInputScreen):
    view_class=HexagramView
    entry_twist_screen='HexagramTwistScreen'

    @staticmethod
    def make_scrambled(cancel=None):
        # Keep the built-in scramble inside the solver's closed whole-material
        # group. An extra arbitrary jumble turn can produce a legal-looking
        # shape that the colour/group solver cannot reduce, especially after
        # repeated manual twists.
        return hexagram_scrambled(cancel=cancel, jumble=False)

    @staticmethod
    def validate_aligned(cube):
        if cube.history:
            # The solver checks the recorded path against the actual state.
            # Its fallback colour group is narrower than the legal turns.
            return
        from solver.hexagram import validate
        validate(observed_colors(cube))


class HexagramTwistScreen(PiscesTwistScreen):
    entry_screen_name='HexagramInputScreen'


class CloverPyraminxInputScreen(PiscesInputScreen):
    from renderer.pisces_view import CloverPyraminxView as view_class
    from cube.clover_pyraminx_aligned import scrambled as _scrambled
    entry_twist_screen='CloverPyraminxTwistScreen'
    make_scrambled=staticmethod(_scrambled)

    @staticmethod
    def validate_aligned(cube):
        from solver.clover_pyraminx import validate
        validate(observed_colors(cube))


class CloverPyraminxTwistScreen(PiscesTwistScreen):
    entry_screen_name='CloverPyraminxInputScreen'
