"""A broken startup checkpoint must not trap subsequent launches."""
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.session import SessionStore, encode, decode
from cube.cube3 import Cube3
from cube.cube4 import Cube4


class Pending:
    def __init__(self, callback, delay):
        self.callback, self.delay, self.cancelled = callback, delay, False

    def cancel(self):
        self.cancelled = True

    def run(self):
        if not self.cancelled: self.callback(self.delay)


@pytest.fixture
def startup(tmp_path, monkeypatch):
    from kivy.clock import Clock
    events = []
    def schedule(callback, delay=0):
        event = Pending(callback, delay)
        events.append(event)
        return event
    monkeypatch.setattr(Clock, 'schedule_once', schedule)
    cube = Cube4.solved()
    entry = SimpleNamespace(_cube=None, _face='F', _data={},
                            view=SimpleNamespace(cube=None), _refresh=lambda: None)
    home = SimpleNamespace()
    screens = {'HomeScreen': home, 'TestEntry': entry}
    class Manager:
        transition = SimpleNamespace(duration=.1, is_active=False)
        _current = 'HomeScreen'
        fail_enter = False
        @property
        def current(self): return self._current
        @current.setter
        def current(self, page):
            self._current = page
            if self.fail_enter and page == 'TestEntry':
                entry.view.cube = app.cube
                app.facelets_cache['partial mutation'] = True
                raise IndexError('damaged restored page')
        @property
        def current_screen(self): return screens[self.current]
        def has_screen(self, name): return name in screens
        def get_screen(self, name): return screens[name]
    notices = []
    app = SimpleNamespace(cube=cube, n=4, puzzle_kind='cube', facelets_cache={4: {'kept': True}},
                          user_data_dir=str(tmp_path), root=Manager(),
                          notify_session_recovery=notices.append)
    store = SessionStore(app)
    fixture = SimpleNamespace(store=store, app=app, entry=entry, events=events, notices=notices,
                              original=cube, raw=None)
    def write(**overrides):
        state = dict(version=1, page='TestEntry', app=dict(n=3, cube=Cube3.solved(),
                     puzzle_kind='cube', facelets_cache={3: {}}),
                     screens={'TestEntry': {'_cube': Cube3.solved(), '_face': 'B'}}, color_info={})
        state.update(overrides)
        fixture.raw = json.dumps(encode(state)).encode('utf-8')
        store.path.write_bytes(fixture.raw)
    fixture.write = write
    yield fixture
    store.close()


def assert_recovered(case):
    store, app = case.store, case.app
    assert not store.restoring
    assert app.root.current == 'HomeScreen'
    assert app.cube is case.original and app.n == 4
    assert app.facelets_cache == {4: {'kept': True}}
    assert not store.path.exists()
    assert not store.recovery.marker.exists()
    assert store.recovery.backup.read_bytes() == case.raw
    assert case.notices == [store.recovery.backup]
    assert store.recovery._handler is None


@pytest.mark.parametrize('invalid', ['{incomplete', 'null', '[]', '{"@":"os:system"}'])
def test_invalid_files_are_isolated_once(startup, invalid):
    case = startup
    case.raw = invalid.encode()
    case.store.path.write_bytes(case.raw)
    case.store.restore()
    assert_recovered(case)
    # A fresh launch never decodes the quarantined file again.
    restarted = SessionStore(case.app)
    restarted.restore()
    assert len(list(case.store.path.parent.glob('last-session.failed-*.json'))) == 1
    assert len(case.notices) == 1


def test_oversized_checkpoint_is_not_decoded(startup, monkeypatch):
    case = startup
    case.raw = b' ' * (16 * 1024 * 1024 + 1)
    case.store.path.write_bytes(case.raw)
    monkeypatch.setattr('app.session.decode', lambda _: pytest.fail('Oversized cache decoded'))
    case.store.restore()
    assert_recovered(case)


def test_obsolete_format_is_backed_up(startup):
    startup.write(version=99)
    startup.store.restore()
    assert_recovered(startup)


def test_error_entering_page_rolls_back_model_drafts_and_view(startup):
    case = startup
    case.write()
    case.app.root.fail_enter = True
    case.store.restore()
    assert_recovered(case)
    assert case.entry._cube is None and case.entry._face == 'F'
    assert case.entry.view.cube is None


def test_error_in_deferred_finish_restores_global_palette(startup):
    from app.constants import COLOR_INFO
    case = startup
    previous = dict(COLOR_INFO)
    case.write(color_info={'W': ('Broken', (0, 0, 0, 1)), 'bad-key': ('Bad', (1, 1, 1, 1))})
    def fail(): raise ValueError('bad saved model geometry')
    case.entry._refresh = fail
    case.store.restore()
    assert case.store.restoring
    case.events[0].run()
    assert_recovered(case)
    assert COLOR_INFO == previous


def test_delayed_kivy_failure_is_handled_only_during_restore(startup):
    from kivy.base import ExceptionManager
    case = startup
    case.write()
    case.store.restore()
    case.events[0].run()  # finish() has run, but first-frame protection is active.
    assert case.store.restoring and case.store.recovery.marker.is_file()
    try: raise IndexError('late animation/draw failure')
    except IndexError as error:
        assert ExceptionManager.handle_exception(error) == ExceptionManager.PASS
    # Guard does not turn an unrelated repeating failure into an infinite loop.
    assert case.store._restore_failed_once
    assert ExceptionManager.handle_exception(ValueError('second failure')) == ExceptionManager.RAISE
    case.events[-1].run()
    assert_recovered(case)
    assert ExceptionManager.handle_exception(ValueError('normal runtime failure')) == ExceptionManager.RAISE
    assert all(event.cancelled for event in case.events[:-1])


def test_valid_restore_keeps_original_file_and_releases_save_after_first_frames(startup):
    case = startup
    case.write()
    case.store.restore()
    assert case.store.recovery.marker.is_file()
    case.store.save(synchronous=True)
    assert case.store.path.read_bytes() == case.raw
    case.events[0].run()
    assert case.app.n == 3 and case.entry._face == 'B'
    assert case.store.restoring
    case.events[-1].run()
    assert not case.store.restoring and not case.store.recovery.marker.exists()
    assert case.store.path.read_bytes() == case.raw
    assert not case.notices and case.store.recovery._handler is None


@pytest.mark.parametrize('closed_normally', [False, True])
def test_interrupted_restore_is_not_retried_next_launch(startup, monkeypatch, closed_normally):
    case = startup
    case.write()
    case.store.restore()
    if closed_normally: case.store.close()
    else: case.store.recovery.unguard()  # simulate process death, marker stays on disk
    # New process starts with defaults, not the old half-restored objects.
    case.app.cube = case.original
    case.app.n = 4
    case.app.facelets_cache = {4: {'kept': True}}
    case.app.root._current = 'HomeScreen'
    monkeypatch.setattr('app.session.decode', lambda _: pytest.fail('Interrupted cache retried'))
    restarted = SessionStore(case.app)
    restarted.restore()
    case.store.close()
    case.store = restarted
    assert_recovered(case)


def test_pending_marker_for_different_checkpoint_does_not_discard_new_input(startup):
    case = startup
    case.write()
    case.store.recovery.marker.write_text(json.dumps({'digest': hashlib.sha256(b'old').hexdigest()}))
    case.store.restore()
    case.events[0].run()
    case.events[-1].run()
    assert case.app.n == 3 and not case.store.restoring
    assert case.store.path.read_bytes() == case.raw
    assert case.store.recovery.backup is None


def test_cannot_move_bad_file_preserves_source_and_blocks_autosave(startup, monkeypatch):
    case = startup
    case.raw = b'broken'
    case.store.path.write_bytes(case.raw)
    replace = __import__('os').replace
    def fail_move(source, dest):
        if str(source) == str(case.store.path): raise PermissionError('file locked')
        return replace(source, dest)
    monkeypatch.setattr('app.session_recovery.os.replace', fail_move)
    case.store.restore()
    assert case.store.recovery.block_save and case.app.root.current == 'HomeScreen'
    case.store.save(synchronous=True)
    assert case.store.path.read_bytes() == case.raw
    assert case.store.recovery.marker.exists()


def test_recovery_allows_new_clean_checkpoint_and_preserves_original_backup(startup):
    case = startup
    case.raw = b'broken'
    case.store.path.write_bytes(case.raw)
    case.store.restore()
    backup = case.store.recovery.backup
    case.store.save(synchronous=True)
    state = decode(json.loads(case.store.path.read_text(encoding='utf-8')))
    assert state['page'] == 'HomeScreen' and state['app']['n'] == 4
    assert backup.read_bytes() == case.raw


def test_separate_failures_never_overwrite_previous_backup(startup):
    case = startup
    case.raw = b'first failure'
    case.store.path.write_bytes(case.raw)
    case.store.restore()
    first = case.store.recovery.backup
    case.store.path.write_bytes(b'second failure')
    case.store.restore()
    assert first.read_bytes() == b'first failure'
    assert case.store.recovery.backup != first
    assert case.store.recovery.backup.read_bytes() == b'second failure'


def test_app_exit_saves_then_releases_restore_guard():
    from app.application import CubeApp
    calls = []
    app = SimpleNamespace(root=SimpleNamespace(has_screen=lambda _: False),
        _autosave_event=SimpleNamespace(cancel=lambda: calls.append('cancel autosave')),
        _session_store=SimpleNamespace(save=lambda **_: calls.append('save'),
                                       close=lambda: calls.append('release guard')))
    CubeApp.on_stop(app)
    assert calls == ['cancel autosave', 'save', 'release guard']
