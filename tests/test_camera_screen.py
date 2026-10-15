"""拍照识别页的构造与流程冒烟测试（无需真实相机/窗口交互）。"""

import pytest

pytest.importorskip("kivy")

from app import i18n


class _FakeTheme:
    def __getattr__(self, name):
        return (0.1, 0.1, 0.1, 1)

    def bind(self, **kwargs):
        pass


class _FakeApp:
    def __init__(self, n=3):
        self.theme = _FakeTheme()
        self.n = n
        self.facelets_input = None


class _FakeManager:
    def __init__(self):
        self.current = None


def _make(monkeypatch, n=3):
    import ui.screens.camera_screen as cs
    app = _FakeApp(n)
    monkeypatch.setattr(cs, "_app", lambda: app)
    return app, cs.CameraScreen()


def test_camera_screen_constructs(monkeypatch):
    app, scr = _make(monkeypatch, 3)
    scr.retranslate()
    scr.refresh_theme()
    assert scr.title.text
    assert scr._ori.current_face() == "F"


def test_camera_screen_face_order_matches_input(monkeypatch):
    from renderer.cube_orientation import SEQ
    app, scr = _make(monkeypatch, 3)
    seen = [scr._ori.current_face()]
    for _ in range(5):
        scr.navigate("next")
        seen.append(scr._ori.current_face())
    assert tuple(seen) == SEQ
    # 继续下一步回到起点
    scr.navigate("next")
    assert scr._ori.current_face() == SEQ[0]


def test_camera_screen_navigate_shows_rotation_hint(monkeypatch):
    app, scr = _make(monkeypatch, 3)
    scr.navigate("next")
    assert scr.msg.text  # 提示转动方向
    from app.i18n import tr
    assert tr("face.R") in scr.msg.text or "R" in scr.msg.text


def test_camera_screen_apply_partial_goes_to_input(monkeypatch):
    app, scr = _make(monkeypatch, 3)
    scr.manager = _FakeManager()
    scr._data = {"F": [["W", "W", "W"], ["W", "W", "W"], ["W", "W", "W"]]}
    scr.apply_to_input()
    assert scr.manager.current == "InputScreen"
    assert app.facelets_input is not None
    assert len(app.facelets_input["F"]) == 3
    # 未拍的面留空
    assert app.facelets_input["R"] == [["", "", ""], ["", "", ""], ["", "", ""]]


def test_camera_back_goes_home(monkeypatch):
    app, scr = _make(monkeypatch, 3)
    scr.manager = _FakeManager()
    scr.go_back()
    assert scr.manager.current == "HomeScreen"


def test_camera_apply_marks_camera_origin(monkeypatch):
    app, scr = _make(monkeypatch, 3)
    scr.manager = _FakeManager()
    scr._data = {"F": [["W", "W", "W"], ["W", "W", "W"], ["W", "W", "W"]]}
    scr.apply_to_input()
    assert getattr(app, "input_from_camera", False) is True
    assert scr.manager.current == "InputScreen"


def test_camera_screen_apply_valid_flow(monkeypatch):
    from cube.conversion import cubies_to_facelets
    from cube.cube3 import Cube3

    app, scr = _make(monkeypatch, 3)
    scr.manager = _FakeManager()
    facelets = cubies_to_facelets(Cube3.solved().cubies, 3)
    scr._data = dict(facelets)
    scr.apply_to_input()
    assert app.facelets_input == facelets
    assert app.n == 3
    assert scr.manager.current == "InputScreen"
