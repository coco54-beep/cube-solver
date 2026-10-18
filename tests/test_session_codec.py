"""Checkpoint serialization checks without a device or a Kivy window."""
import importlib
import json

import numpy as np
import pytest

from app.session import decode, encode


@pytest.mark.parametrize('module,symbol,kwargs', [
    ('cube.cube2', 'Cube2', {}),
    ('cube.cube3', 'Cube3', {}),
    ('cube.cube4', 'Cube4', {}),
    ('cube.cube5', 'Cube5', {}),
    ('cube.cube_n', 'CubeN', {'n': 6}),
    ('cube.mastermorphix', 'MastermorphixCube', {'n': 4}),
    ('cube.mirror', 'MirrorCube', {}),
    ('cube.shape_cube', 'AxisCube', {}),
    ('cube.shape_cube', 'PandoraCube', {}),
    ('cube.mirror_tower', 'MirrorTowerCube', {}),
    ('cube.square1', 'Square1Cube', {}),
])
def test_puzzle_json_round_trip(module, symbol, kwargs):
    cube = getattr(importlib.import_module(module), symbol).solved(**kwargs)
    record = encode(cube)
    restored = decode(json.loads(json.dumps(record)))
    assert type(restored) is type(cube)
    assert encode(restored) == record


def test_entered_polyhedral_colors_round_trip():
    from cube.polyhedral import PolyhedralPuzzle
    cube = PolyhedralPuzzle('megaminx', 5)
    cube.apply_move(cube.moves()[0])
    cube.colors[0] = -1
    restored = decode(json.loads(json.dumps(encode(cube))))
    assert restored.colors == cube.colors


def test_scan_samples_and_manual_choices_round_trip():
    samples = np.arange(300, dtype=np.uint8).reshape(2, 2, 3, 25)
    data = {'samples': samples, 'manual': {(1, 0): 'O'}, 'recorded': {0, 2}}
    restored = decode(json.loads(json.dumps(encode(data))))
    assert np.array_equal(restored['samples'], samples)
    assert restored['manual'] == data['manual']
    assert restored['recorded'] == data['recorded']


def test_unknown_checkpoint_type_rejected():
    with pytest.raises(ValueError, match='Unknown checkpoint type'):
        decode({'@': 'os:system', 'v': {}})


def test_input_checkpoint_is_written_and_restored(monkeypatch, tmp_path):
    pytest.importorskip("kivy")
    from types import SimpleNamespace
    from cube.cube3 import Cube3
    from app.session import ENTRY_NAMES, SessionStore
    from kivy.clock import Clock
    cube = Cube3.solved()
    partial = {'F': [['W', '', 'O'], ['', 'G', ''], ['', '', '']]}
    screens = {name: SimpleNamespace() for name in ENTRY_NAMES}
    screens['InputScreen'] = SimpleNamespace(
        _cube=cube, _face='F', _data=partial,
        collect_facelets=lambda: partial,
        _refresh_view=lambda: None, _update_progress=lambda: None)
    class Manager:
        current = 'InputScreen'
        transition = SimpleNamespace(duration=0)
        @property
        def current_screen(self): return screens[self.current]
        def get_screen(self, name): return screens[name]
        def has_screen(self, name): return name in screens
    app = SimpleNamespace(n=3, puzzle_kind='cube', cube=cube,
                          root=Manager(), user_data_dir=str(tmp_path))
    store = SessionStore(app)
    store.save(synchronous=True)
    assert store.path.is_file()
    app.n = 5
    screens['InputScreen']._data = {}
    screens['InputScreen']._face = 'D'
    monkeypatch.setattr(Clock, 'schedule_once', lambda callback, delay: callback(delay))
    store.restore()
    assert app.n == 3
    assert app.cube is screens['InputScreen']._cube
    assert screens['InputScreen']._data == partial
    assert screens['InputScreen']._face == 'F'
    assert not store.restoring
