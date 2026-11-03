"""Truncated caps, true overlapping jumbling and state-only colour recovery."""
import json
from collections import Counter
import pytest
from cube.edge_jumbling import Helicopter14Cube
from cube.helicopter_14_aligned import generators,scrambled,observed_colors
from cube.polyhedral import Move
from cube.curvy_copter import JUMBLE
from app.session import encode,decode


def test_gold_is_one_colour_on_eight_real_caps_and_all_45_cells_are_present():
    c=Helicopter14Cube()
    assert len(c.solids)==45 and len(c.panels)==32
    assert Counter(c.paints)=={0:4,1:4,2:4,3:4,4:4,5:4,6:8}
    assert {f for h,f,p in c.panels}==set(range(14))
    assert len(c.geometry.spec.normals)==14 and c.color_count==7
    assert c.regular_colours().is_solved() and c.is_solved()


def test_preparation_opens_an_overlapping_turn_and_blocked_axes_are_atomic():
    c=Helicopter14Cube();before=c.signature();prepared=set(c.selection(0))
    c.apply_move(Move(0,0,JUMBLE));shaped=c.signature()
    assert any(prepared&set(c.selection(a)) for a in (3,4))
    assert not c.can_apply(Move(1,0,180.))
    with pytest.raises(ValueError,match='rigid.blocked'):c.apply_move(Move(1,0,180.))
    assert c.signature()==shaped
    c.apply_move(Move(3,0,180.));c.apply_move(Move(3,0,-180.));c.apply_move(Move(0,0,-JUMBLE))
    assert c.signature()==before


def test_all_closed_exchanges_restore_material_and_permute_real_fields():
    base=Helicopter14Cube();rows=generators()
    assert len(rows)==36 and sum(len(w)==5 for p,w in rows)==24
    for action,word in rows:
        c=base.clone().apply_moves(word)
        assert c.aligned_permutation()==action
        c.apply_moves(tuple(Move(m.axis,0,-m.amount) for m in reversed(word)))
        assert c.signature()==base.signature()


@pytest.mark.parametrize('length',(30,100))
@pytest.mark.parametrize('seed',range(6))
@pytest.mark.parametrize('shape',(False,True))
def test_independent_reentry_solve_without_scramble_history(seed,length,shape):
    from solver.edge_jumbling import solve
    source=scrambled(seed,length,jumble=shape)
    if shape:
        c=decode(json.loads(json.dumps(encode(source))))
        c=Helicopter14Cube.from_observation(json.loads(json.dumps(c.observation_data())))
        assert any(not c.frame_aligned(h,f) for h,f in enumerate(c.frames))
    else:c=Helicopter14Cube(paints=observed_colors(source))
    assert not hasattr(c,'history');before=c.signature()
    word=solve(c,seconds=20)
    assert c.clone().apply_moves(word).is_solved()
    assert c.signature()==before


def test_solver_and_scramble_cancel_preserve_input():
    from solver.edge_jumbling import solve
    c=scrambled(1,30);before=c.signature()
    with pytest.raises(InterruptedError):solve(c,cancel=lambda:True)
    with pytest.raises(TimeoutError):solve(c,seconds=0.)
    with pytest.raises(InterruptedError):scrambled(3,100,cancel=lambda:True)
    assert c.signature()==before


def test_actual_background_service_and_shared_routes_use_the_new_solver():
    from services.solve_service import SolveService
    from app.application import CubeApp
    from types import SimpleNamespace
    from threading import Event
    from ui.screens.polyhedral_screen import _entry_for,_view_for
    from renderer.edge_jumbling_view import EdgeJumblingView
    from ui.screens.copter_screen import PLAY_ONLY_KINDS
    app=SimpleNamespace();CubeApp.new_polyhedral(app,'helicopter_14',3)
    assert isinstance(app.cube,Helicopter14Cube)
    assert _entry_for(app.cube)=='EdgeJumblingInputScreen' and _view_for(app.cube) is EdgeJumblingView
    assert 'helicopter_14' in PLAY_ONLY_KINDS
    c=scrambled(13,100);before=c.signature();event=Event();results=[]
    def done(result):results.append(result);event.set()
    service=SolveService();service.start(c,done)
    assert event.wait(20) and results[0].success
    assert c.clone().apply_moves(results[0].moves).is_solved() and c.signature()==before


def test_seven_colour_renderer_keeps_all_gold_fields_and_legacy_checkpoint_is_separate():
    from renderer.edge_jumbling_view import EdgeJumblingView
    from renderer.polyhedral_view import default_palette
    from cube.polyhedral import PolyhedralPuzzle
    c=scrambled(2,30);view=EdgeJumblingView()
    rows=view._surfaces(c)
    assert {r[3] for r in rows if r[3] is not None}==set(range(32))
    assert view.palette==default_palette(c) and len(view.palette)==7
    old=PolyhedralPuzzle('helicopter_14',3)
    restored=decode(json.loads(json.dumps(encode(old))))
    assert isinstance(restored,PolyhedralPuzzle) and restored.is_solved()
