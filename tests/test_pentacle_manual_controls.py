"""Enter visible angles and paint with the actual blank-screen controls."""
import json
import random
from pathlib import Path
from types import SimpleNamespace
from time import monotonic
import pytest
pytest.importorskip('kivy')
from tests.test_bandaged_manual_controls import pump,until,Tap,CaptureSolve
from tests.test_circle_manual_controls import point_for
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager,NoTransition
from app.theme import Theme
from cube.pentacle import PentacleCube
from cube.polyhedral import Move
from solver.pentacle_state import disc_corrections,panel_key
from services.solve_service import SolveService
from ui.screens.pentacle_screen import PentacleScreen


@pytest.mark.parametrize('seed',(37,20261023))
def test_actual_angles_colour_controls_and_solve(monkeypatch,seed):
    rng=random.Random(seed);source=PentacleCube()
    for _ in range(40):
        face=rng.randrange(6);source.apply_moves(source.alignment_moves(face))
        source.apply_move(Move(face,1,rng.choice((90,180,270))))
    for face in range(6):source.apply_move(Move(face,0,rng.randint(-1800,1800)/10))
    observed={panel_key(p):c for p,c in zip(source.world_panels(),source._paints)}
    phases=tuple(-v for v in disc_corrections(source))
    blank=PentacleCube(paints=[-1]*len(source.panels))
    app=SimpleNamespace(cube=blank,theme=Theme(),polyhedral_solution=None,puzzle_kind='pentacle',n=3)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    manager=ScreenManager(transition=NoTransition());screen=PentacleScreen(name='PentacleScreen')
    capture=CaptureSolve(name='SolvingScreen');manager.add_widget(screen);manager.add_widget(capture)
    Window.add_widget(manager)
    try:
        for _ in range(4):pump()
        for _ in range(6):
            face=screen._face
            screen.disc_angle.value=phases[face]
            screen.apply_disc.dispatch('on_release')
            desired={i:observed[panel_key(p)] for i,p in enumerate(blank.world_panels())
                     if blank.geometry.stickers[i].face==face}
            for colour in range(6):
                screen._swatches[colour].dispatch('on_release')
                for i,c in desired.items():
                    if c!=colour:continue
                    touch=Tap(point_for(screen.view,i))
                    assert screen.view.on_touch_down(touch)
                    assert screen.view.on_touch_up(touch)
                    assert blank._paints[i]==colour
            next(b for b in screen.walk() if getattr(b,'icon_name',None)=='next').dispatch('on_release')
            until(lambda:not screen._view_busy)
        assert {panel_key(p):c for p,c in zip(blank.world_panels(),blank._paints)}==observed
        next(b for b in screen.walk() if getattr(b,'icon_name',None)=='solve').dispatch('on_release')
        assert manager.current=='SolvingScreen'
        cube=capture.entered;assert not cube.history
        started=monotonic();results=[]
        cancel=SimpleNamespace(is_set=lambda:monotonic()-started>20.)
        SolveService()._run(cube,results.append,None,cancel)
        assert len(results)==1 and results[0].success,results
        word=results[0].moves
        replay=cube.clone();replay.apply_moves(word);assert replay.is_solved()
        row=dict(kind='pentacle',seed=seed,core_turns=40,actual_controls=True,solve_service=True,history_empty=True,
                 disc_phases=phases,visible_colours=blank._paints,success=True,replay_solved=True,
                 moves=len(word),solve_seconds=round(monotonic()-started,3))
        path=Path('reports/input-audit/2026-10-23/pentacle-manual-inputs')/(str(seed)+'.json')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(row,indent=2),encoding='utf-8')
    finally:
        screen.reset_interaction();Window.remove_widget(manager);pump()
