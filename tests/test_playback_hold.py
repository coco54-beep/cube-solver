"""测试回放页每步之间的停留（hold）逻辑。"""

import types

from kivy.clock import Clock

import ui.screens.playback_screen as ps
from ui.screens.playback_screen import PlaybackScreen

ps._app = lambda: types.SimpleNamespace(n=4)


class _FakeView:
    def __init__(self):
        self._anim = None

    def set_cube(self, c):
        pass

    def _draw_mesh(self):
        pass

    def _cancel_animation(self):
        pass


class _FakeCube:
    def clone(self):
        return _FakeCube()

    def apply_move(self, mv):
        pass

    def apply_moves(self, mvs):
        pass


def test_hold_delays_next_step():
    sc = PlaybackScreen()
    sc.build_ui()
    sc.view = _FakeView()
    sc._work = _FakeCube()
    sc._moves = ["R", "U"]
    sc._idx = -1
    sc._playing = False
    sc._busy = False
    sc._queue = []
    sc._hold = 0.5
    sc._hold_ev = None

    calls = []
    real_advance = sc._advance

    def tracked_advance():
        calls.append(sc._idx)
        real_advance()

    sc._advance = tracked_advance

    def sync_animate(step):
        sc._after_turn(step)

    sc._animate_step = sync_animate

    # 点击播放：立即走第一步
    sc.toggle_play()
    assert sc._idx == 0
    assert len(calls) == 1
    # 一步完成后应安排停留计时器，而非立即走下一步
    assert sc._hold_ev is not None
    # 模拟停留计时器到期
    sc._do_advance()
    assert len(calls) == 2
    assert sc._idx == 1
    sc._do_advance()
    assert sc._playing is False


def test_hold_zero_advances_immediately():
    sc = PlaybackScreen()
    sc.build_ui()
    sc.view = _FakeView()
    sc._work = _FakeCube()
    sc._moves = ["R", "U"]
    sc._idx = -1
    sc._playing = True
    sc._busy = False
    sc._queue = []
    sc._hold = 0.0
    sc._hold_ev = None

    advanced = []
    sc._advance = lambda: advanced.append(True)

    sc._schedule_next()
    assert advanced == [True]
    assert sc._hold_ev is None
