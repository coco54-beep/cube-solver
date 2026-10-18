"""Piece-shape entry for the third- and fourth-order Mirror Pyraminxes."""
from cube.mirror_pyraminx import MirrorPyraminxCube, placements
from renderer.mirror_pyraminx_view import MirrorPyraminxView
from ui.screens.mirror_tower_screen import MirrorTowerScreen


class MirrorPyraminxScreen(MirrorTowerScreen):
    cube_class = MirrorPyraminxCube
    view_class = MirrorPyraminxView
    hint_key = 'mirror_pyraminx.hint'

    def _placements(self, home, position):
        return placements(self._cube.n, home, position)

    def entry_center_preset(self):
        # Silver centres carry a visible direction, so enter their shape too.
        return set()

    def _refresh(self):
        super()._refresh()
        # A formula tutorial needs its own shape cases before being offered.
        self.demo_button.disabled = True
        self.demo_button.opacity = 0
