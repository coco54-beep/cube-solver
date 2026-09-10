"""拧魔方回写状态的回归测试。

关键点：拧动改变了魔方状态后，必须作废 app.solve_result，否则
InputScreen.start_solve 的复用判断（facelets_input == 当前 facelets）
会命中拧动前的旧解法，导致按“求解”后无法正确还原。
"""

import types

import pytest

pytest.importorskip("kivy")

from cube.cube5 import Cube5

import ui.screens.twist_screen as twist_screen


@pytest.mark.quick
def test_write_back_invalidates_stale_solve_result(monkeypatch):
    app = types.SimpleNamespace(
        n=5,
        facelets_input={"stale": True},
        solve_result=object(),  # 模拟“之前求解过”留下的结果
    )
    monkeypatch.setattr(twist_screen, "_app", lambda: app)

    captured = {}

    class _FakeInputScreen:
        def set_facelets(self, facelets):
            captured["facelets"] = facelets

    fake_self = types.SimpleNamespace(
        _input_screen=lambda: _FakeInputScreen(),
        _work=Cube5.solved(),
    )

    twist_screen.TwistScreen._write_back(fake_self)

    assert app.facelets_input is captured["facelets"]
    assert app.solve_result is None

    # 复刻 start_solve 的复用判断：状态已变，不得复用旧结果。
    prev_result = app.solve_result
    prev_layout = app.facelets_input
    current = captured["facelets"]
    assert not (prev_result is not None and prev_layout == current)
