"""Shape-card input screens for mirror Axis/Windmill/Fisher cubes."""
from cube.mirror_shape import (MirrorAxisCube, MirrorFisherCube,
                               MirrorUnequalWindmillCube, MirrorUnequalFisherCube,
                               MirrorOffsetWindmillCube, MirrorOffsetFisherCube,
                               MirrorWindmillCube, shape_groups, shell_signature,
                               normalize_shape_input, equivalent_shells, shape_orientations)
from cube.mastermorphix import MorphixInputError, placements
from app.i18n import tr
from renderer.mirror_shape_view import (MirrorAxisView, MirrorFisherView,
                                       MirrorUnequalWindmillView, MirrorUnequalFisherView,
                                       MirrorOffsetWindmillView, MirrorOffsetFisherView,
                                       MirrorWindmillView)
from ui.screens.mirror_screen import MirrorScreen


class MirrorShapeScreen(MirrorScreen):
    def entry_center_preset(self):
        # Shaped centres have a visible direction and must be entered too.
        return set()

    def available_homes(self, pos):
        group_of, _ = shape_groups(self._cube.shape_kind)
        representatives = {}
        for home in super().available_homes(pos):
            representatives.setdefault(group_of[home], home)
        return list(representatives.values())

    def _same_piece(self, left, right):
        groups, _ = shape_groups(self._cube.shape_kind)
        return groups[left] == groups[right]

    def choose_piece(self, home, frame=None):
        if not self.entry_can_edit():
            return
        frame = frame or placements(home, self._pos)[0]
        # Gallery representatives are shared; prefer an unused hidden identity
        # whenever it has the exact same polygon placement.
        used = {piece.home for pos, piece in self._cube.cubies.items()
                if pos in self._recorded and pos != self._pos}
        choices = equivalent_shells(self._cube.shape_kind, home, frame, self._pos)
        home, frame = next(((h, f) for h, f in choices if h not in used), (home, frame))
        super().choose_piece(home, frame)

    def _refresh(self):
        super()._refresh()
        if self._cube is not None:
            piece = self._cube.cubies[self._pos]
            self.rotate.disabled = (self._pos not in self._recorded or len(
                shape_orientations(self._cube.shape_kind, piece.home, self._pos)) <= 1)

    def rotate_piece(self):
        if self.rotate.disabled or not self.entry_can_edit():
            return
        piece = self._cube.cubies[self._pos]
        kind = self._cube.shape_kind
        variants = shape_orientations(kind, piece.home, self._pos)
        signature = shell_signature(kind, piece.home, piece.frame)
        start = next((i for i, (home, frame) in enumerate(variants)
                      if shell_signature(kind, home, frame) == signature), -1)
        home, frame = variants[(start + 1) % len(variants)]
        self.choose_piece(home, frame)

    def check(self):
        if len(self._recorded) != len(self._all_positions()):
            self.hint.text = tr('morphix.error.incomplete', total=len(self._all_positions()))
            return None
        try:
            cube = normalize_shape_input(self._cube)
        except MorphixInputError as exc:
            self.hint.text = tr(f'morphix.error.{exc}')
            return None
        self.hint.text = tr('poly.valid')
        return cube


class MirrorWindmillScreen(MirrorShapeScreen):
    cube_class = MirrorWindmillCube
    view_class = MirrorWindmillView


class MirrorAxisScreen(MirrorShapeScreen):
    cube_class = MirrorAxisCube
    view_class = MirrorAxisView


class MirrorFisherScreen(MirrorShapeScreen):
    cube_class = MirrorFisherCube
    view_class = MirrorFisherView


class MirrorUnequalWindmillScreen(MirrorShapeScreen):
    cube_class = MirrorUnequalWindmillCube
    view_class = MirrorUnequalWindmillView


class MirrorUnequalFisherScreen(MirrorShapeScreen):
    cube_class = MirrorUnequalFisherCube
    view_class = MirrorUnequalFisherView


class MirrorOffsetWindmillScreen(MirrorShapeScreen):
    cube_class = MirrorOffsetWindmillCube
    view_class = MirrorOffsetWindmillView


class MirrorOffsetFisherScreen(MirrorShapeScreen):
    cube_class = MirrorOffsetFisherCube
    view_class = MirrorOffsetFisherView
