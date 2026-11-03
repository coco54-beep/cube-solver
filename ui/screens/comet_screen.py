"""Comet uses the shared continuous paint, pose, undo and twist controls."""
from app.i18n import tr
from cube.crazy_comet import scrambled,observed_colors
from renderer.comet_view import CometView
from ui.screens.copter_screen import CopterInputScreen,CopterTwistScreen


class CometInputScreen(CopterInputScreen):
    view_class=CometView
    entry_twist_screen='CometTwistScreen'
    make_scrambled=staticmethod(scrambled)

    @staticmethod
    def validate_aligned(cube):
        from solver.crazy_comet import validate
        validate(observed_colors(cube))

    def _pose_refresh(self):
        self.pose_piece.text=tr('comet.piece',number=self._pose_home+1)
        self.pose_preview.selected_piece=self._pose_home
        self.pose_preview.cube=self._pose_work;self.pose_preview.refresh()


class CometTwistScreen(CopterTwistScreen):
    entry_screen_name='CometInputScreen'


from renderer.comet_view import LanlanCometView
from cube.lanlan_comet_aligned import scrambled as physical_scrambled


class LanlanCometInputScreen(CometInputScreen):
    view_class=LanlanCometView
    entry_twist_screen='LanlanCometTwistScreen'
    make_scrambled=staticmethod(physical_scrambled)

    @staticmethod
    def validate_aligned(cube):
        from solver.lanlan_comet import validate
        validate(observed_colors(cube))


class LanlanCometTwistScreen(CopterTwistScreen):
    entry_screen_name='LanlanCometInputScreen'
