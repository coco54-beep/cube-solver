"""Shape-card input for the ordinary third-order Mirror Skewb."""
from cube.mirror_skewb import MirrorSkewbCube
from cube.mirror_pyraminx import placements
from renderer.mirror_skewb_view import MirrorSkewbView
from ui.screens.mirror_tower_screen import MirrorTowerScreen


class MirrorSkewbScreen(MirrorTowerScreen):
    cube_class = MirrorSkewbCube
    view_class = MirrorSkewbView
    hint_key = 'mirror_skewb.hint'

    def _placements(self, home, position):
        return placements(self._cube.n, home, position, 'skewb')

    def entry_center_preset(self):
        return set()

    def _face_roll(self, index):
        return 0

    def _refresh(self):
        super()._refresh()
        self.demo_button.disabled = True
        self.demo_button.opacity = 0
