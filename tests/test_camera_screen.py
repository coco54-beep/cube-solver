"""拍照识别页的构造与流程冒烟测试（无需真实相机/窗口交互）。"""

import tempfile

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
        self._storage = tempfile.TemporaryDirectory(prefix="cube-camera-test-")
        self.user_data_dir = self._storage.name
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
    monkeypatch.setattr(scr.grid, 'animate_whole_turn', lambda *args, on_done, **kwargs: on_done())
    seen = [scr._ori.current_face()]
    for _ in range(5):
        scr.navigate("next")
        seen.append(scr._ori.current_face())
    assert tuple(seen) == SEQ
    # 继续下一步回到起点
    scr.navigate("next")
    assert scr._ori.current_face() == SEQ[0]


def test_camera_navigation_commits_only_after_animation(monkeypatch):
    app, scr = _make(monkeypatch, 3)
    callbacks = []
    monkeypatch.setattr(scr.grid, 'animate_whole_turn', lambda *args, on_done, **kwargs: callbacks.append(on_done))
    scr.navigate('next')
    assert scr._ori.current_face() == 'F' and scr._turning
    scr.navigate('next')
    assert len(callbacks) == 1
    callbacks[0]()
    assert scr._ori.current_face() == 'R' and not scr._turning


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


def test_camera_cancel_restores_controls_and_keeps_input(monkeypatch):
    _, scr = _make(monkeypatch, 2)
    scr._data = {'F': [['W', 'Y'], ['O', 'B']]}
    scr._scan_job = object()
    previous = scr.btn_prev.disabled
    scr._set_recognizing(True)
    assert scr.btn_prev.disabled and not scr.scan_cancel.disabled
    scr.cancel_recognition()
    assert scr._scan_job is None and not scr._recognizing
    assert scr.btn_prev.disabled == previous and scr.scan_cancel.disabled
    assert scr._data == {'F': [['W', 'Y'], ['O', 'B']]}


def test_camera_calibration_survives_new_screen(monkeypatch, tmp_path):
    from app import prefs
    monkeypatch.setattr(prefs, '_PREFS_FILE', str(tmp_path/'prefs.json'))
    monkeypatch.setattr(prefs, '_LEGACY_FILE', str(tmp_path/'missing.json'))
    _, scr = _make(monkeypatch, 2)
    scr._standard_palette = tuple((.2, .3, .4, 1.) for _ in range(6))
    scr._calibrated_codes = {'Y', 'O'}
    scr._save_calibration()
    _, restored = _make(monkeypatch, 3)
    restored._load_calibration()
    assert restored._standard_palette == scr._standard_palette
    assert restored._calibrated_codes == {'Y', 'O'}


def test_camera_parked_photo_round_trip(monkeypatch):
    import numpy as np
    _, scr = _make(monkeypatch, 2)
    image = np.arange(120*80*3, dtype=np.uint8).reshape(120, 80, 3)
    scr._source_image = image
    scr._photo_dirty = True
    scr.guide.set_image((80, 120))
    scr._park_photo(drop=True)
    assert scr._source_image is None and scr._parked_digest
    monkeypatch.setattr(scr, '_release_source', lambda: None)
    monkeypatch.setattr(scr, '_set_preview', lambda image: None)
    scr._restore_parked_photo()
    assert np.array_equal(scr._source_image, image)


def test_camera_mismatched_photo_does_not_replace_input(monkeypatch):
    import numpy as np
    _, scr = _make(monkeypatch, 2)
    scr._data = {'F': [['W', 'Y'], ['O', 'B']]}
    scr._source_image = np.zeros((40, 40, 3), dtype=np.uint8)
    scr._photo_dirty = True
    scr.guide.set_image((40, 40))
    scr._park_photo(drop=True)
    np.save(scr._parked_image_path, np.ones((40, 40, 3), dtype=np.uint8))
    scr._restore_parked_photo()
    assert scr._source_image is None
    assert scr._parked_quad is None
    assert scr._data == {'F': [['W', 'Y'], ['O', 'B']]}


def test_camera_resume_defers_texture_restore_until_next_frame(monkeypatch):
    from kivy.clock import Clock
    _, scr = _make(monkeypatch, 2)
    scr._active = True
    callbacks=[]
    calls=[]
    monkeypatch.setattr(Clock,'schedule_once',lambda callback,delay:callbacks.append(callback))
    monkeypatch.setattr(scr,'_restore_parked_photo',lambda:calls.append('restore'))
    monkeypatch.setattr(scr,'_ensure_source',lambda:calls.append('source'))
    scr.resume_camera()
    assert calls == []
    callbacks[-1](.2)
    assert calls == ['restore','source']


def test_camera_deferred_resume_stops_if_paused_again(monkeypatch):
    from kivy.clock import Clock
    _, scr = _make(monkeypatch, 2)
    scr._active = True
    callbacks=[]
    monkeypatch.setattr(Clock,'schedule_once',lambda callback,delay:callbacks.append(callback))
    def unexpected(): raise AssertionError('A paused screen recreated a texture')
    monkeypatch.setattr(scr,'_restore_parked_photo',unexpected)
    scr.resume_camera()
    scr._suspended = True
    callbacks[-1](.2)


def test_camera_late_entry_does_not_clear_restored_scan(monkeypatch):
    from types import SimpleNamespace
    from kivy.clock import Clock
    from cube.cube3 import Cube3
    from app.session import ENTRY_NAMES, SessionStore
    app, scr = _make(monkeypatch, 3)
    app.cube = Cube3.solved()
    app.puzzle_kind = 'cube'
    screens = {name: SimpleNamespace() for name in ENTRY_NAMES}
    screens['CameraScreen'] = scr
    class Manager:
        current = 'CameraScreen'
        transition = SimpleNamespace(duration=0)
        current_screen = scr
        def get_screen(self,name): return screens[name]
        def has_screen(self,name): return name in screens
    app.root = Manager()
    scr._data = {'F': [['W','Y','O'], ['B','G','R'], ['O','Y','W']]}
    expected = scr._data
    store = SessionStore(app)
    store.save(synchronous=True)
    scr._data = {}
    callbacks=[]
    monkeypatch.setattr(Clock,'schedule_once',lambda callback,delay:callbacks.append(callback))
    monkeypatch.setattr(scr,'_ensure_source',lambda:None)
    store.restore()
    callbacks[-1](.1)
    assert scr._data == expected
    # Simulate the first transition dispatching on_enter after restore finished.
    scr.on_enter()
    assert scr._data == expected
