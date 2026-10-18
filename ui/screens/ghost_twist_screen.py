"""Legal Ghost turns: show alignment before turning a different axis."""
from app.i18n import tr
from cube.ghost import inverse_move, band_token
from renderer.turn import decompose_move
from renderer.camera_follow import follow_turn, layer_target
from ui.screens.morphix_twist_screen import MorphixTwistScreen, _app
from ui.widgets.buttons import UIButton
from ui.widgets import metrics as m


class GhostTwistScreen(MorphixTwistScreen):
    def _build(self):
        super()._build()
        self.align_button = UIButton(text=tr('ghost.align_toggle'), size_hint_y=None, height=m.h(44))
        self.align_button.bind(on_release=lambda *_: self.toggle_alignment())
        self.panel.add_widget(self.align_button)

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self.face.values = ('1','2','3','4','5') if self._work.n == 1 else ('U','R','F','D','L','B')
        self.face.text = self.face.values[0]
        self.align_button.disabled = self._work.n == 1
        self.btn_wide.disabled = self._work.n == 1
        self._recorded_before = set(self._recorded)

    def twist(self, move):
        if self._busy or self._work is None:
            return
        if self._work.n == 1:
            if isinstance(move, str):
                face = move[0].upper()
            else:
                if move.axis not in range(3,8):
                    return
                face = str(move.axis-2)
            if face not in ('1','2','3','4','5'):
                return
            tokens = ['@F:'+face]
        else:
            if not isinstance(move, str):
                tokens = [band_token(move.axis, move.layer_positions, 90*move.sign)]
            else:
                tokens = [move]
            if any(not self._work.can_turn_axis(step.axis) for token in tokens for step in decompose_move(token,self._work.n)):
                tokens = self._work.alignment_moves() + tokens
        self._history.append(tuple(tokens))
        self._future.clear()
        self._run_tokens(tokens)

    def toggle_alignment(self):
        if self._busy or self._work.n == 1:
            return
        tokens = self._work.alignment_moves(restore=all(abs(a) < 1e-8 for a in self._work.phases))
        self._history.append(tuple(tokens))
        self._future.clear()
        self._run_tokens(tokens)

    def undo(self):
        if self._busy or not self._history:
            return
        tokens = self._history.pop()
        self._future.append(tokens)
        self._run_tokens([inverse_move(t) for t in reversed(tokens)])

    def redo(self):
        if self._busy or not self._future:
            return
        tokens = self._future.pop()
        self._history.append(tokens)
        self._run_tokens(tokens)

    def _run_tokens(self, tokens):
        self.view.cancel_touch()
        self._busy = True
        self.panel.disabled = True
        pending = list(tokens)
        def advance():
            if not pending:
                self._recorded = {pos for pos,piece in self._work.cubies.items()
                                  if piece.home in {p.home for pos,p in self.manager.get_screen(self._source)._cube.cubies.items()
                                                    if pos in self._recorded_before}}
                self.view.recorded = self._recorded
                self._busy = False
                self.panel.disabled = False
                _app().solve_result = None
                self._update_controls()
                return
            token = pending.pop(0)
            step = decompose_move(token, self._work.n)[0]
            def done():
                self._work.apply_move(token)
                self.view.set_cube(self._work)
                advance()
            def begin():
                self.view.start_turn(step.axis, step.layers[0], step.angle, .3,
                                     on_done=done, layer_positions=step.layers,
                                     include_fixed_centers=token.startswith(('@G','@F')))
            follow_turn(self.view,layer_target(step.axis,step.layers),begin)
        advance()
