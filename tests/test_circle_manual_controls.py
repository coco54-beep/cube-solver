"""Fill blank circle puzzles through real swatches, picked panels and arrows."""
import json
from pathlib import Path
from types import SimpleNamespace
from time import monotonic
import pytest

from tests.test_bandaged_manual_controls import pump,until,Tap,CaptureSolve
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager,NoTransition
from app.theme import Theme
from cube.circle_cube import Circle2Cube,KINDS
from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble
from solver.polyhedral import solve_polyhedral
from ui.screens.polyhedral_screen import PolyhedralScreen


def point_for(view,index):
    view._draw()
    for polygon,slot in view._polygons:
        if slot!=index:continue
        for b,c in zip(polygon[1:],polygon[2:]):
            p=(view.x+(polygon[0][0]+b[0]+c[0])/3,view.y+(polygon[0][1]+b[1]+c[1])/3)
            if view.pick(*p)==index:return p
    raise AssertionError(('Panel has no selectable visible point',index))


@pytest.mark.parametrize('kind',('circle_2',)+KINDS)
def test_visible_scramble_reenters_with_real_controls(monkeypatch,kind):
    source=Circle2Cube() if kind=='circle_2' else PolyhedralPuzzle(kind,3)
    scramble(source,40,20261023)
    blank=Circle2Cube(colors=[-1]*48) if kind=='circle_2' else PolyhedralPuzzle(kind,3,[-1]*len(source.colors))
    app=SimpleNamespace(cube=blank,theme=Theme(),polyhedral_solution=None,puzzle_kind=kind,n=blank.n)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    manager=ScreenManager(transition=NoTransition());screen=PolyhedralScreen(name='PolyhedralScreen')
    capture=CaptureSolve(name='SolvingScreen');manager.add_widget(screen);manager.add_widget(capture)
    Window.add_widget(manager)
    try:
        for _ in range(4):pump()
        for _ in range(6):
            for colour in range(6):
                screen._swatches[colour].dispatch('on_release')
                for i,sticker in enumerate(blank.geometry.stickers):
                    if sticker.face!=screen._face or source.colors[i]!=colour:continue
                    touch=Tap(point_for(screen.view,i))
                    assert screen.view.on_touch_down(touch)
                    assert screen.view.on_touch_up(touch)
                    assert blank.colors[i]==colour
            next(b for b in screen.walk() if getattr(b,'icon_name',None)=='next').dispatch('on_release')
            until(lambda:not screen._view_busy)
        assert blank.colors==source.colors
        next(b for b in screen.walk() if getattr(b,'icon_name',None)=='solve').dispatch('on_release')
        assert manager.current=='SolvingScreen'
        entered=capture.entered
        assert not entered.circle_history and entered.colors==source.colors
        started=monotonic();word=solve_polyhedral(entered)
        replay=entered.clone()
        for move in word:replay.apply_move(move)
        assert replay.is_solved()
        report=dict(kind=kind,seed=20261023,scramble_turns=40,actual_controls=True,
                    history_empty=True,visible_colors=entered.colors,success=True,replay_solved=True,
                    moves=len(word),solve_seconds=round(monotonic()-started,3))
        path=Path('reports/input-audit/2026-10-23/circle-manual-inputs')/(kind+'.json')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    finally:
        screen.reset_interaction();Window.remove_widget(manager);pump()
