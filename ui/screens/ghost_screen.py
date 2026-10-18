"""Shape-card entry for the four commercial Ghost models."""
from app.i18n import tr
from cube.ghost import GhostCube, ghost_piece, ghost_placements
from renderer.ghost_view import GhostView
from ui.screens.mirror_screen import MirrorScreen
from ui.widgets.buttons import UIButton
from ui.widgets import metrics as m


class GhostScreen(MirrorScreen):
    cube_class = GhostCube
    view_class = GhostView
    entry_twist_screen = 'GhostTwistScreen'

    def build_ui(self):
        super().build_ui()
        self.reference_label.height = m.h(44)
        self.reference_label.bind(width=lambda w,width:setattr(w,'text_size',(width,None)))
        self.alignment_button = UIButton(text=tr('ghost.align_toggle'), size_hint_y=None, height=m.h(44))
        self.alignment_button.bind(on_release=lambda *_: self.toggle_alignment())
        self._controls.add_widget(self.alignment_button)

    def entry_center_preset(self):
        return {(0,0,0)} if self._cube is not None and self._cube.n == 1 else set()

    def _card_camera(self, view, pos):
        if self._cube.n == 1:
            view.camera.azimuth = 0.
            view.camera.elevation = 0.
            view._redraw()
        else:
            super()._card_camera(view,pos)

    def _placements(self, home, pos):
        return ghost_placements(self._cube.n, home, pos)

    def available_homes(self, pos):
        if self._cube.n == 3 and sum(v != 0 for v in pos) == 1:
            return [pos]
        return super().available_homes(pos)

    def _make_piece(self, home, pos, frame):
        return ghost_piece(self._cube.n, home, pos, frame)

    def _preview_cube(self, pos, piece):
        return GhostCube({pos: piece}, n=self._cube.n, phases=self._cube.phases)

    def _refresh(self):
        super()._refresh()
        if self._cube is None:
            return
        self.demo_button.disabled = True
        self.demo_button.opacity = 0
        self.reference_label.text = tr('ghost.floppy' if self._cube.n == 1 else 'ghost.reference')
        self.hint.text = tr('ghost.input_hint')
        if self._cube.n == 1:
            from cube.ghost_floppy import CORE, EDGES, CORNERS
            key, number = ('core', 0) if self._pos == CORE else ('edge', EDGES.index(self._pos)+1) if self._pos in EDGES else ('corner', CORNERS.index(self._pos)+1)
            self.slot.text = tr('ghost.floppy_'+key, i=number)
            self.hint.text = tr('ghost.floppy_input')
            self.view.show_axes = True
            self.view._redraw()
        self.alignment_button.disabled = self._cube.n == 1

    def toggle_alignment(self):
        if not self.entry_can_edit() or self._cube.n == 1:
            return
        self._remember()
        self._cube.apply_moves(self._cube.alignment_moves(restore=all(abs(a) < 1e-8 for a in self._cube.phases)))
        self._refresh()

    def turn_view(self, direction):
        if self._cube.n != 1:
            return super().turn_view(direction)
        if self._busy_turn:
            return
        self.view.cancel_touch()
        self._busy_turn = True
        self._pending_dir = direction
        self._controls.disabled = True
        self.view.animate_whole_turn((0.,1.,0.), direction*180., .55, on_done=self._after_view_turn)

    def _after_view_turn(self):
        if self._cube.n != 1:
            return super()._after_view_turn()
        from renderer.mat4 import Mat4
        self._ori.index = 3 if self._ori.index == 0 else 0
        self._ori.world = Mat4.rotation_axis(180. if self._ori.index == 3 else 0., (0.,1.,0.))
        self._pending_dir = None
        self._busy_turn = False
        self._controls.disabled = False
        self.view.set_whole_world(self._ori.world)

    def rotate_piece(self):
        if not self.entry_can_edit() or self._pos not in self._recorded:
            return
        piece = self._cube.cubies[self._pos]
        options = self._placements(piece.home, self._pos)
        if len(options) < 2:
            return
        self._remember()
        frame = options[(options.index(piece.frame)+1) % len(options)]
        self._cube.cubies[self._pos] = self._make_piece(piece.home, self._pos, frame)
        self._refresh()

    def random_load(self):
        if not self.entry_can_edit():
            return
        from random import Random
        from cube.scramble import random_scramble
        work = GhostCube.solved(n=self._cube.n)
        if work.n == 1:
            rng = Random()
            work.apply_moves(['@F:'+str(rng.randrange(1,6)) for _ in range(20)])
        else:
            work.apply_moves(work.alignment_moves())
            work.apply_moves(random_scramble(work.n))
        self._remember()
        self._cube = work
        self._recorded = set(work.positions)
        self._refresh()

    def check(self):
        if self._recorded != set(self._cube.positions):
            self.hint.text = tr('morphix.error.incomplete', total=len(self._cube.positions))
            return None
        if len({piece.home for piece in self._cube.cubies.values()}) != len(self._cube.positions):
            self.hint.text = tr('ghost.invalid')
            return None
        if any(piece.frame not in self._placements(piece.home, pos) for pos, piece in self._cube.cubies.items()):
            self.hint.text = tr('ghost.invalid')
            return None
        self.hint.text = tr('poly.valid')
        return self._cube.clone()

    def open_help(self):
        from kivy.uix.label import Label
        from kivy.uix.popup import Popup
        from ui.widgets.dialogs import theme_popup
        from ui.screens.mastermorphix_screen import _app
        text = (tr('ghost.floppy')+'\n\n'+tr('ghost.floppy_input') if self._cube.n == 1 else
                tr('ghost.input_hint')+'\n\n'+tr('ghost.reference'))
        label = Label(text=text, halign='center', valign='middle')
        label.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        popup = Popup(title=tr('directory.ghost'), content=label, size_hint=(.86,.46))
        theme_popup(popup, _app().theme)
        popup.open()
