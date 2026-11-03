"""Public material puzzles start solved and offer play, not manual editing."""
import os
from types import SimpleNamespace
from time import monotonic,sleep
import pytest
os.environ.setdefault('KIVY_NO_ARGS','1')
os.environ.setdefault('KIVY_METRICS_DENSITY','1')
os.environ.setdefault('KIVY_DPI','96')
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.config import Config
Config.set('graphics','window_state','hidden')
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen,ScreenManager,NoTransition
from app.application import CubeApp,_screen
from app.theme import Theme
from ui.screens.copter_screen import PLAY_ONLY_KINDS
from app.fonts import setup_cjk_font
from pathlib import Path

CASES=(
 ('new_copter','lanlan_curvy_copter','CopterInputScreen','CopterTwistScreen'),
 ('new_lanlan_comet','lanlan_comet_physical','LanlanCometInputScreen','LanlanCometTwistScreen'),
 ('new_twins','mf8_twins','TwinsInputScreen','TwinsTwistScreen'),
 ('new_suncube','mf8_suncube_2','SunCubeInputScreen','SunCubeTwistScreen'),
 ('new_hexagram','lanlan_hexagram','HexagramInputScreen','HexagramTwistScreen'),
 ('new_flower_copter','lanlan_flower_copter','FlowerCopterInputScreen','FlowerCopterTwistScreen'),
 ('new_butterflower','lanlan_butterflower','ButterflowerInputScreen','ButterflowerTwistScreen'))


def pump():
    Clock.tick();Builder.sync();Clock.tick_draw();Builder.sync();Window.flip()


def until(predicate):
    deadline=monotonic()+12
    while not predicate() and monotonic()<deadline:pump();sleep(.005)
    assert predicate()


class CaptureSolve(Screen):
    def configure(self,cube,*args):self.entered=cube.clone()


@pytest.fixture(params=CASES,ids=lambda row:row[1])
def page(request,monkeypatch):
    factory,kind,entry_name,twist_name=request.param
    app=App();app.theme=Theme();app.polyhedral_solution=None;app.solve_result=None
    app.input_from_camera=False;app.simple_input=True;app.selection_series=None
    getattr(CubeApp,factory)(app)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    # KV rules are global. Loading at collection time poisons unrelated tests
    # that intentionally create standalone controls without a running App.
    setup_cjk_font();kv=str(Path(__file__).resolve().parents[1]/'ui/kv/app.kv')
    already_loaded=kv in Builder.files
    if not already_loaded:Builder.load_file(kv)
    manager=ScreenManager(transition=NoTransition())
    entry=_screen(entry_name);entry.name=entry_name
    twist=_screen(twist_name);twist.name=twist_name
    capture=CaptureSolve(name='SolvingScreen')
    manager.add_widget(entry);manager.add_widget(twist);manager.add_widget(capture)
    manager.add_widget(Screen(name='HomeScreen'));Window.add_widget(manager)
    for _ in range(3):pump()
    yield app,manager,entry,twist,capture,request.param
    entry.reset_interaction();twist.view.cancel_animation();twist.view.cancel_touch()
    Window.remove_widget(manager);pump()
    if not already_loaded:Builder.unload_file(kv)
    app.dispatch('on_stop')


def test_scope_keeps_the_existing_seven_and_five_new_jumbling_models():
    assert PLAY_ONLY_KINDS=={row[1] for row in CASES}|{'helicopter','helicopter_14','rua','clover','mf8_bauhinia_minx'}


def test_factory_and_page_open_a_complete_solved_model_without_input_controls(page):
    app,manager,entry,twist,capture,(_,kind,_,_)=page
    assert app.cube.puzzle_kind==kind and app.cube.is_solved()
    assert all(c>=0 for c in app.cube.paints)
    assert entry.play_only and entry.view.on_pick is None
    assert all(widget.parent is None for widget in
               (entry.palette,entry.palette2,*entry._extra_palette_rows,entry.navigation,entry.hint,entry.shape_button))
    assert not entry.status.text
    root=entry._root_layout
    if root.width>root.height*1.1:
        assert root.body.orientation=='horizontal' and entry.view.right<=root.panel_viewport.x+1
    assert 'clear' in entry._play_actions.hidden_keys
    assert set(entry._play_actions.buttons)-entry._play_actions.hidden_keys=={'twist','random','undo','target','solve'}
    before=app.cube.signature();entry._color=1;entry.paint(0);entry.clear()
    entry.open_shape_entry();entry.open_palette_settings()
    assert app.cube.signature()==before and getattr(entry,'_pose_popup',None) is None


def test_twist_return_reset_undo_and_solve_keep_the_played_state(page):
    app,manager,entry,twist,capture,_=page
    initial=app.cube.signature()
    entry.open_twist();assert manager.current==twist.name
    move=next(m for m in app.cube.moves() if app.cube.can_apply(m))
    twist.twist(move)
    until(lambda:twist.view._move is None and not twist.view.camera_busy)
    assert app.cube.signature()!=initial
    played=app.cube.signature();twist.back();pump()
    assert manager.current==entry.name and app.cube.signature()==played
    entry.undo();assert app.cube.signature()==initial
    app.cube.apply_move(move);entry.assign_initial()
    assert app.cube.is_solved()
    entry.undo();assert app.cube.signature()==played
    entry.assign_initial();entry.solve()
    assert manager.current=='SolvingScreen' and capture.entered.is_solved()


def test_old_blank_input_restores_to_a_complete_model(page):
    app,manager,entry,twist,capture,_=page
    manager.current='HomeScreen'
    blank=type(app.cube)();blank.paints=(-1,)*len(blank.panels);app.cube=blank
    manager.current=entry.name;pump()
    assert app.cube.is_solved() and all(c>=0 for c in app.cube.paints)
    assert entry._cube is app.cube


def test_scramble_and_undo_still_work_without_manual_input(page):
    app,manager,entry,twist,capture,_=page
    initial=app.cube.signature();entry.randomize()
    until(lambda:entry._job is None)
    assert all(c>=0 for c in app.cube.paints)
    assert app.cube.signature()!=initial
    entry.undo();assert app.cube.signature()==initial


def test_scramble_failure_preserves_model_and_unlocks_actions(page,monkeypatch):
    app,manager,entry,twist,capture,_=page
    initial=app.cube.signature()
    def fail(**kwargs):raise TimeoutError('copter.scramble_timeout')
    monkeypatch.setattr(entry,'make_scrambled',fail)
    entry.randomize();until(lambda:entry._job is None)
    assert app.cube.signature()==initial and entry.entry_can_edit()
    assert entry.status.text and entry._entry_notice


def test_legacy_twins_scramble_upgrades_the_model_and_undo_restores_the_exact_old_state(page):
    app,manager,entry,twist,capture,(_,kind,_,_)=page
    if kind!='mf8_twins':pytest.skip('Twins geometry transition')
    from cube.twins_state import TwinsState
    from cube.twins_pcubes import TwinsPCubesState
    from cube.polyhedral import Move
    from cube.curvy_copter import JUMBLE
    legacy=TwinsState().apply_move(Move(0,0,JUMBLE));before=legacy.signature()
    app.cube=entry._cube=legacy;entry.view.set_cube(legacy);entry._history=[]
    entry.randomize();until(lambda:entry._job is None)
    assert isinstance(entry._cube,TwinsPCubesState) and app.cube is entry._cube
    updated=entry._cube.signature()
    entry.open_twist();until(lambda:manager.current==twist.name)
    assert isinstance(twist._cube,TwinsPCubesState)
    twist.back();until(lambda:manager.current==entry.name)
    assert entry._cube.signature()==updated
    entry.undo()
    assert type(entry._cube) is TwinsState and app.cube is entry._cube
    assert entry._cube.signature()==before
    entry.randomize();until(lambda:entry._job is None)
    assert isinstance(entry._cube,TwinsPCubesState)


def test_failed_legacy_twins_scramble_keeps_the_old_geometry_and_colours(page,monkeypatch):
    app,manager,entry,twist,capture,(_,kind,_,_)=page
    if kind!='mf8_twins':pytest.skip('Twins geometry transition')
    from cube.twins_state import TwinsState
    legacy=TwinsState();before=legacy.signature()
    app.cube=entry._cube=legacy;entry.view.set_cube(legacy);entry._history=[]
    def fail(**kwargs):raise TimeoutError('copter.scramble_timeout')
    monkeypatch.setattr(entry,'make_scrambled',fail)
    entry.randomize();until(lambda:entry._job is None)
    assert entry._cube is legacy and app.cube is legacy
    assert legacy.signature()==before and not entry._history and entry.entry_can_edit()
