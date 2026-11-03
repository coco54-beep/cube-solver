"""Restore only the current model/order; malformed old drafts must be atomic."""
import os
from copy import deepcopy
from types import SimpleNamespace
import pytest
os.environ.setdefault('KIVY_NO_ARGS','1')
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.app import App
from app.theme import Theme
from cube.cube3 import Cube3
from cube.cube4 import Cube4
from app.constants import FACES
from ui.screens.input_screen import InputScreen


def data(n,color=''):
    result={f:[['']*n for _ in range(n)] for f in FACES};result['F'][0][0]=color
    return result


@pytest.fixture
def editor(monkeypatch):
    app=SimpleNamespace(n=3,puzzle_kind='cube',cube=Cube3.solved(),theme=Theme(),simple_input=False,
        facelets_input=None,facelets_cache={},bandage_entry_cache={},solve_result=None)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    screen=InputScreen();yield screen,app
    screen.reset_interaction()


def test_wrong_order_global_draft_uses_valid_order_cache(editor):
    screen,app=editor;app.n=4;app.cube=Cube4.solved()
    app.facelets_input=data(2,'G');app.facelets_cache[4]=data(4,'R')
    screen.on_enter()
    assert screen.collect_facelets()==data(4,'R')
    assert app.facelets_cache[4]==data(4,'R')


def test_wrong_order_draft_without_compatible_cache_opens_blank(editor):
    screen,app=editor;app.n=4;app.cube=Cube4.solved();app.facelets_input=data(2,'G')
    screen.on_enter();assert screen.collect_facelets()==data(4)


@pytest.mark.parametrize('invalid',(data(2,'R'),data(4,'R'),{'F':[['W']]},
    {'F':None},None,{'F':[['W']*3]*2+[None]}))
def test_bad_set_facelets_preserves_existing_draft_and_undo(editor,invalid):
    screen,app=editor;screen.on_enter();screen.set_facelets(data(3,'B'),remember=True)
    before=screen.collect_facelets();history=deepcopy(screen._history)
    assert screen.set_facelets(invalid,remember=True) is False
    assert screen.collect_facelets()==before and screen._history==history


def test_departing_page_saves_its_own_order_after_app_changes(editor):
    screen,app=editor;screen.on_enter();screen.set_facelets(data(3,'G'))
    app.n=4;app.cube=Cube4.solved();app.facelets_cache[4]=data(4,'R')
    screen.on_pre_leave()
    assert app.facelets_cache[3]==data(3,'G') and app.facelets_cache[4]==data(4,'R')
    screen.on_enter();assert screen.collect_facelets()==data(4,'R')


def test_legacy_valid_draft_still_restores(editor):
    screen,app=editor;app.facelets_input=data(3,'B')
    screen.on_enter();assert screen.collect_facelets()==data(3,'B')


def test_owned_fresh_input_overrides_older_cache(editor):
    screen,app=editor;app.facelets_input=data(3,'R');app.facelets_input_key=3
    app.facelets_cache[3]=data(3,'G')
    screen.on_enter();assert screen.collect_facelets()==data(3,'R')


def test_equal_size_different_model_does_not_reuse_global_colours(editor):
    from cube.penrose_entry import solved
    screen,app=editor;screen.on_enter();screen.set_facelets(data(3,'O'));screen.on_pre_leave()
    app.puzzle_kind='penrose_3';app.cube=solved(3);app.facelets_cache['penrose_3']=data(3,'G')
    screen.on_enter();assert screen.collect_facelets()==data(3,'G')


def test_corrupt_cached_grid_is_ignored(editor):
    screen,app=editor;app.facelets_cache[3]={'F':None}
    screen.on_enter();assert screen.collect_facelets()==data(3)


def test_writeback_before_larger_order_page_enters_is_safe(editor):
    screen,app=editor;screen.on_enter();screen.set_facelets(data(3,'G'))
    app.n=4;app.cube=Cube4.solved()
    assert screen.set_facelets(data(4,'R'),remember=True)
    assert screen.collect_facelets()==data(4,'R')
    screen.on_pre_leave()
    assert app.facelets_cache[4]==data(4,'R')


def test_partial_writeback_before_order_change_initializes_other_faces(editor):
    screen,app=editor;screen.on_enter();app.n=4;app.cube=Cube4.solved()
    assert screen.set_facelets({'F':data(4,'R')['F']},remember=True)
    assert screen.collect_facelets()==data(4,'R')


def test_restore_rejects_wrong_sized_saved_screen_without_losing_cache(editor,monkeypatch,tmp_path):
    import json
    from app.session import SessionStore,encode,ENTRY_NAMES
    from kivy.clock import Clock
    screen,app=editor;screen.on_enter();app.user_data_dir=str(tmp_path)
    screens={name:SimpleNamespace() for name in ENTRY_NAMES};screens['InputScreen']=screen
    class Manager:
        current='InputScreen';transition=SimpleNamespace(duration=0)
        def has_screen(self,name):return name in screens
        def get_screen(self,name):return screens[name]
    app.root=Manager();state=dict(version=1,page='InputScreen',replay_to=None,
        app=dict(n=4,puzzle_kind='cube',cube=Cube4.solved(),facelets_input=data(2,'G'),facelets_cache={4:data(4,'R')}),
        screens={'InputScreen':{'_data':data(2,'G')}},color_info={})
    store=SessionStore(app);store.path.write_text(json.dumps(encode(state)),encoding='utf-8')
    original=store.path.read_bytes()
    monkeypatch.setattr(Clock,'schedule_once',lambda callback,delay=0:callback(delay))
    store.restore()
    assert screen.collect_facelets()==data(4,'R') and store.path.read_bytes()==original
