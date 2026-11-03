"""Regression coverage for queued buttons, busy editors and solve transitions."""
import os
from copy import deepcopy
from types import SimpleNamespace

import pytest

os.environ.setdefault('KIVY_NO_ARGS','1')
from app.desktop_runtime import configure_graphics
configure_graphics()
pytest.importorskip('kivy')
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen, ScreenManager, NoTransition
from kivy.uix.widget import Widget
from app.theme import Theme
from cube.cube3 import Cube3


@pytest.fixture
def app(monkeypatch):
    app=SimpleNamespace(theme=Theme(),cube=Cube3.solved(),n=3,puzzle_kind='cube',
        simple_input=False,facelets_input=None,facelets_cache={},solve_result=None,
        polyhedral_solution=None,selection_series=None,input_from_camera=False)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    yield app
    Clock.tick()


def shape_editor(app,kind):
    if kind=='morphix':
        from cube.mastermorphix import MastermorphixCube
        from ui.screens.mastermorphix_screen import MastermorphixScreen
        app.cube=MastermorphixCube.solved();app.mastermorphix_palette=app.cube.palette
        screen=MastermorphixScreen(name='MastermorphixScreen')
    elif kind=='mirror':
        from cube.mirror import MirrorCube
        from ui.screens.mirror_screen import MirrorScreen
        app.cube=MirrorCube.solved();app.mastermorphix_palette=app.cube.palette
        screen=MirrorScreen(name='MirrorScreen')
    else:
        from cube.mirror_tower import MirrorTowerCube
        from ui.screens.mirror_tower_screen import MirrorTowerScreen
        app.cube=MirrorTowerCube.solved()
        screen=MirrorTowerScreen(name='MirrorTowerScreen')
    app.puzzle_kind=app.cube.puzzle_kind
    screen.on_pre_enter()
    return screen


def shape_snapshot(screen):
    pieces=getattr(screen._cube,'cubies',getattr(screen._cube,'pieces',None))
    return repr(pieces),set(screen._recorded),len(screen._history)


@pytest.mark.parametrize('kind',('morphix','mirror','tower'))
@pytest.mark.parametrize('busy',('camera','job'))
def test_shape_cards_ignore_release_while_busy(app,kind,busy):
    screen=shape_editor(app,kind)
    card=screen.gallery.children[-1]
    before=shape_snapshot(screen)
    if busy=='camera':screen.view.camera_busy=True
    else:screen._job=object()
    try:
        card.dispatch('on_release')
        assert shape_snapshot(screen)==before
    finally:
        screen.view.camera_busy=False;screen._job=None
        screen.reset_interaction()


@pytest.mark.parametrize('kind',('morphix','mirror','tower'))
def test_removed_card_cannot_edit_a_new_position(app,kind):
    screen=shape_editor(app,kind)
    card=screen.gallery.children[-1]
    if kind=='tower':
        target=next(i for i,s in enumerate(screen._cube.geometry.stickers)
                    if s.piece!=screen._position)
        screen.paint(target)
    else:
        target=next(p for p in screen._all_positions() if p!=screen._pos)
        screen.select_position(target)
    before=shape_snapshot(screen)
    card.dispatch('on_release')
    assert shape_snapshot(screen)==before
    screen.reset_interaction()


@pytest.mark.parametrize('action',('fill','next','previous','paint'))
def test_ordinary_input_cannot_edit_during_camera_follow(app,action):
    from ui.screens.input_screen import InputScreen
    screen=InputScreen(name='InputScreen')
    before=screen.collect_facelets(),len(screen._history),screen._ori.index
    screen.view.camera_busy=True
    try:
        if action=='fill':screen.fill_face()
        elif action=='next':screen.next_face()
        elif action=='previous':screen.prev_face()
        else:screen.on_cell(0,0,screen._ori.current_face())
        assert (screen.collect_facelets(),len(screen._history),screen._ori.index)==before
        assert not screen._busy_turn
    finally:
        screen.view.camera_busy=False;screen.reset_interaction()


class Preview(Widget):
    def set_cube(self,cube):self.cube=cube


def test_cancel_before_solve_page_enters_never_starts_worker(app,monkeypatch):
    from ui.screens.solving_screen import SolvingScreen
    from services.solve_service import SolveService
    calls=[]
    monkeypatch.setattr(SolveService,'start',lambda *a,**kw:calls.append(kw))
    manager=ScreenManager(transition=NoTransition())
    manager.add_widget(Screen(name='InputScreen'))
    screen=SolvingScreen(name='SolvingScreen');manager.add_widget(screen)
    screen.configure(app.cube,'InputScreen',view_factory=Preview)
    screen.on_cancel()
    screen.on_enter()  # A transition's queued enter event is already pending.
    assert not calls
    assert manager.current=='InputScreen'


def test_cancelled_solve_late_result_cannot_navigate(app,monkeypatch):
    from ui.screens.solving_screen import SolvingScreen
    from services.solve_service import SolveService
    monkeypatch.setattr(SolveService,'start',lambda *a,**kw:None)
    manager=ScreenManager(transition=NoTransition())
    manager.add_widget(Screen(name='InputScreen'))
    screen=SolvingScreen(name='SolvingScreen');manager.add_widget(screen)
    screen.configure(app.cube,'InputScreen',view_factory=Preview)
    screen.on_enter();run=screen._run;screen.on_cancel()
    screen._finish(SimpleNamespace(success=True),run)
    assert manager.current=='InputScreen'
    assert app.solve_result is None


def test_large_palette_has_touch_sized_rows_and_saves_last_colour(app):
    from ui.screens.piece_palette_screen import PiecePaletteScreen
    colors=[(i/33,.25,1-i/33,1.) for i in range(32)]
    captured=[]
    source=Screen(name='Source')
    source.palette_colors=lambda:colors
    source.default_palette_colors=lambda:colors
    source.palette_title=lambda:'32 colours'
    source.apply_palette_colors=lambda values:captured.append(values)
    manager=ScreenManager(transition=NoTransition());manager.add_widget(source)
    page=PiecePaletteScreen(name='PiecePaletteScreen');manager.add_widget(page)
    page.size=(400,850);page.configure(source)
    assert page.swatch_row.cols<=6
    assert page.swatch_row.height>=44*2
    page.reference.size=(368,145);page.reference._draw()
    assert len(page.reference._labels)==32
    assert all(label.width>=30 and label.font_size>=10 for label in page.reference._labels)
    page._swatches[-1].dispatch('on_release')
    assert page._index==31
    page.save()
    assert captured==[colors]


@pytest.mark.parametrize('n',(3,4))
def test_penrose_edge_card_links_two_sides_and_undo_redo(app,n):
    from cube.penrose_entry import solved
    from cube.coordinates import pos_from_rc
    from ui.screens.input_screen import InputScreen
    app.n=n;app.cube=solved(n);app.puzzle_kind=f'penrose_{n}'
    screen=InputScreen(name='InputScreen');before=screen.collect_facelets()
    screen.on_cell(0,1,'F');panel=screen.penrose_edges
    pos=panel.position;choice=panel.choices[1]
    panel.choose(pos,choice)
    entered=screen.collect_facelets()
    changed=[(f,r,c) for f in before for r in range(n) for c in range(n)
             if before[f][r][c]!=entered[f][r][c]]
    assert len(changed)==2
    assert {pos_from_rc(n,f,r,c) for f,r,c in changed}=={pos}
    panel.flip();assert screen.collect_facelets()!=entered
    panel.flip();assert screen.collect_facelets()==entered
    screen.undo();screen.redo();assert screen.collect_facelets()==entered
    screen.reset_interaction()


def test_penrose_removed_card_is_inert_after_reselecting(app):
    from cube.penrose_entry import solved
    from ui.screens.input_screen import InputScreen
    app.cube=solved(3);app.puzzle_kind='penrose_3'
    screen=InputScreen(name='InputScreen')
    screen.on_cell(0,1,'F');card=screen.penrose_edges.gallery.children[-1]
    screen.on_cell(1,0,'F');before=screen.collect_facelets()
    card.dispatch('on_release')
    assert screen.collect_facelets()==before


def test_square_family_removed_card_cannot_fill_the_new_slot(app):
    from cube.square_family import SquareFamilyCube
    from ui.screens.square_family_screen import SquareFamilyScreen
    app.cube=SquareFamilyCube('square2');app.puzzle_kind='square2'
    screen=SquareFamilyScreen(name='SquareFamilyScreen');screen.on_pre_enter()
    card=screen.gallery.children[-1]
    screen.select_slot(6)
    before=repr((screen._entry.slots,screen._entry.blocks)),len(screen._history)
    card.dispatch('on_release')
    assert (repr((screen._entry.slots,screen._entry.blocks)),len(screen._history))==before
    screen.reset_interaction()


def test_large_palette_old_swatch_cannot_select_invalid_new_index(app):
    from ui.screens.piece_palette_screen import PiecePaletteScreen
    source=Screen(name='Source');source.palette_title=lambda:'Colours'
    colors=[(i/33,.25,1-i/33,1.) for i in range(32)]
    source.palette_colors=source.default_palette_colors=lambda:colors
    page=PiecePaletteScreen();page.configure(source);old=page._swatches[-1]
    colors=colors[:4];page.configure(source)
    old.dispatch('on_release')
    assert 0<=page._index<len(page._draft)


def test_polyhedral_twist_cannot_start_second_camera_turn(app):
    from cube.polyhedral import PolyhedralPuzzle
    from ui.screens.polyhedral_screen import PolyhedralTwistScreen
    app.cube=PolyhedralPuzzle('fto',3)
    screen=PolyhedralTwistScreen();screen.on_pre_enter()
    before=screen._face
    screen.view.camera_busy=True
    screen.change_view(1)
    assert screen._face==before
    screen.on_leave()


def test_reconfiguring_solve_after_early_cancel_starts_only_new_request(app,monkeypatch):
    from ui.screens.solving_screen import SolvingScreen
    from services.solve_service import SolveService
    started=[]
    monkeypatch.setattr(SolveService,'start',lambda self,cube,**kw:started.append(cube))
    manager=ScreenManager(transition=NoTransition());manager.add_widget(Screen(name='InputScreen'))
    screen=SolvingScreen(name='SolvingScreen');manager.add_widget(screen)
    screen.configure(app.cube,'InputScreen',view_factory=Preview);screen.on_cancel()
    latest=app.cube.clone();latest.apply_moves(['R'])
    screen.configure(latest,'InputScreen',view_factory=Preview);screen.on_enter()
    assert len(started)==1 and not started[0].is_solved()
    screen.on_cancel()


def test_duplicate_solve_request_keeps_the_active_worker(app,monkeypatch):
    from ui.screens.solving_screen import SolvingScreen
    from services.solve_service import SolveService
    started=[]
    monkeypatch.setattr(SolveService,'start',lambda self,cube,**kw:started.append(cube))
    manager=ScreenManager(transition=NoTransition());manager.add_widget(Screen(name='InputScreen'))
    screen=SolvingScreen(name='SolvingScreen');manager.add_widget(screen)
    screen.configure(app.cube,'InputScreen',view_factory=Preview)
    manager.current='SolvingScreen';screen.on_enter();run=screen._run
    screen.configure(app.cube,'InputScreen',view_factory=Preview)
    assert screen._run is run and len(started)==1
    assert screen._pending is None
    screen.on_cancel()


def test_late_progress_from_cancelled_solve_cannot_change_new_request(app,monkeypatch):
    from ui.screens.solving_screen import SolvingScreen
    from services.solve_service import SolveService
    monkeypatch.setattr(SolveService,'start',lambda *a,**kw:None)
    manager=ScreenManager(transition=NoTransition());manager.add_widget(Screen(name='InputScreen'))
    screen=SolvingScreen(name='SolvingScreen');manager.add_widget(screen)
    screen.configure(app.cube,'InputScreen',view_factory=Preview)
    screen.on_enter();previous=screen._run;screen.on_cancel()
    screen.configure(app.cube,'InputScreen',view_factory=Preview);screen.on_enter()
    screen._progress_for(previous,{'progress':1.})
    assert screen.progress.value==0
    screen.on_cancel()


def test_releasing_pressed_button_after_leaving_page_does_nothing(app):
    from ui.widgets.buttons import UIButton
    manager=ScreenManager(transition=NoTransition())
    source=Screen(name='Source');target=Screen(name='Target')
    manager.add_widget(source);manager.add_widget(target)
    button=UIButton();source.add_widget(button);calls=[]
    button.bind(on_release=lambda *_:calls.append(True))
    button.state='down'
    touch=SimpleNamespace(grab_current=button,ungrab=lambda owner:None)
    manager.current='Target'
    assert button.on_touch_up(touch)
    assert button.state=='normal' and not calls


def test_page_change_dismisses_old_confirmation(app,monkeypatch):
    from kivy.uix.popup import Popup
    from ui.widgets.dialogs import theme_popup
    manager=ScreenManager(transition=NoTransition())
    manager.add_widget(Screen(name='Source'));manager.add_widget(Screen(name='Target'))
    app.root=manager
    popup=theme_popup(Popup(),app.theme);dismissed=[]
    monkeypatch.setattr(popup,'dismiss',lambda *a,**kw:dismissed.append(True))
    manager.current='Target'
    assert dismissed==[True]
    popup.dispatch('on_dismiss')


def test_camera_old_turn_callback_cannot_finish_a_new_turn(monkeypatch):
    from tests.test_camera_screen import _make
    _,screen=_make(monkeypatch,3)
    callbacks=[]
    monkeypatch.setattr(screen.grid,'animate_whole_turn',lambda *a,on_done,**kw:callbacks.append(on_done))
    screen.navigate('next');screen._cancel_turn()
    screen.navigate('next')
    callbacks[0]()
    assert screen._ori.current_face()=='F' and screen._turning
    callbacks[1]()
    assert screen._ori.current_face()=='R' and not screen._turning
