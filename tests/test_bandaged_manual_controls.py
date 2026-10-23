"""Re-enter generated bandages through the real empty screen and controls."""
import json
import os
from pathlib import Path
from time import monotonic,sleep
from types import SimpleNamespace

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
from app.theme import Theme
from cube.bandaged_cube import BandagedCube,KINDS
from cube.bandaged_entry import plates
from cube.conversion import cubies_to_facelets
from cube.coordinates import pos_from_rc
from ui.screens.input_screen import InputScreen


def pump():
    Clock.tick();Builder.sync();Clock.tick_draw();Builder.sync();Window.flip()


def until(predicate):
    deadline=monotonic()+8
    while not predicate() and monotonic()<deadline:pump();sleep(.005)
    assert predicate()


class CaptureSolve(Screen):
    def configure(self,cube,*args):self.entered=cube.clone()


class Tap:
    def __init__(self,pos):self.pos=pos;self.x,self.y=pos
    def grab(self,widget):self.owner=widget
    def ungrab(self,widget):self.owner=None


@pytest.mark.parametrize('kind',tuple(KINDS))
def test_empty_input_real_controls_match_a_24_turn_scramble(monkeypatch,kind):
    source=BandagedCube.random_scramble(kind,24,20261023)
    target=cubies_to_facelets(source.cubies,source.n)
    inventory=plates(source)
    app=SimpleNamespace(cube=BandagedCube.solved(kind),n=source.n,puzzle_kind=kind,
        theme=Theme(),facelets_input=None,solve_result=None,polyhedral_solution=None,
        facelets_cache={},bandage_entry_cache={},simple_input=False)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    manager=ScreenManager(transition=NoTransition())
    screen=InputScreen(name='InputScreen');capture=CaptureSolve(name='SolvingScreen')
    manager.add_widget(screen);manager.add_widget(capture)
    Window.add_widget(manager)
    try:
        for _ in range(4):pump()
        screen.clear_all()
        assert not any(c for grid in screen._data.values() for row in grid for c in row)
        for face_index in range(6):
            face=screen._ori.current_face()
            for plate in [p for p in inventory if p.face==face]:
                button=next(b for b in screen.bandage_row.children if b.text.endswith('· '+plate.shape))
                button.dispatch('on_release')
                if len({r for r,c in plate.cells})>len({c for r,c in plate.cells}):
                    screen.bandage_rotate.dispatch('on_release')
                r,c=min(plate.cells)
                screen.picker.select(target[face][r][c])
                screen.view._draw_mesh()
                pos=pos_from_rc(source.n,face,r,c)
                quad=next(q for q,p,f in screen.view._last_quads if p==pos and f==face)
                touch=Tap((sum(p['x'] for p in quad)/4,sum(p['y'] for p in quad)/4))
                assert screen.view.on_touch_down(touch)
                assert screen.view.on_touch_up(touch)
                assert screen._bandage_pending==(face,r,c)
                screen.bandage_confirm.dispatch('on_release')
                assert (face,plate.cells) in screen._bandage_connections,screen.msg.text
            if face_index<5:
                screen.btn_next.dispatch('on_release')
                until(lambda:not screen._busy_turn)
        assert screen.collect_facelets()==target
        assert screen._bandage_connections=={(p.face,p.cells) for p in inventory}
        assert not app.cube.history and app.cube.is_solved()
        screen.btn_solve.dispatch('on_release')
        assert manager.current=='SolvingScreen',screen.msg.text
        entered=capture.entered
        assert not entered.history
        assert cubies_to_facelets(entered.cubies,entered.n)==target
        assert {(p.face,p.cells) for p in plates(entered)}==screen._bandage_connections
        path=Path('reports/input-audit/2026-10-23/bandaged-manual-inputs')/(kind+'.json')
        path.parent.mkdir(parents=True,exist_ok=True)
        # The solver receives only what the input screen captured. Source
        # cubie IDs, frames, scramble tokens and inverse paths are excluded.
        payload=dict(kind=kind,seed=20261023,scramble_turns=24,facelets=target,
                     plates=[dict(face=p.face,cells=p.cells) for p in inventory],
                     actual_controls=True,entered_history_empty=True)
        path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    finally:
        screen.reset_interaction()
        Window.remove_widget(manager)
        pump()
