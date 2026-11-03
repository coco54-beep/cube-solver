"""Real CAD shape states, obstruction, independent repair and play-only routing."""
import json
import math
from types import SimpleNamespace
import pytest
from cube.polyhedral import Move
from cube.curvy_copter import JUMBLE
from cube.flower_copter import FlowerCopterCube
from cube.twins_state import TwinsState,SECOND

CASES=(('flower',FlowerCopterCube),('twins',TwinsState))


@pytest.mark.parametrize('kind,factory',CASES)
@pytest.mark.parametrize('first',(Move(0,0,JUMBLE),Move(12,0,60.)))
def test_shape_turns_move_whole_coloured_material_and_reverse_exactly(kind,factory,first):
    cube=factory();before=cube.signature();paints=cube.paints;members=set(cube.selection(first.axis))
    cube.apply_move(first)
    assert cube.paints==paints and len(cube.frames)==len(before[0])
    assert any(abs(v)>1.01 for p in cube.world_panels() for q in p for v in q)
    assert all(cube.frames[h]==factory().frames[h] for h in range(len(cube.frames)) if h not in members)
    cube.validate_pose()
    with pytest.raises(ValueError,match='copter.align_first'):cube.aligned_permutation()
    cube.apply_move(Move(first.axis,0,-first.amount))
    assert cube.signature()==before and cube.is_solved()


@pytest.mark.parametrize('kind,factory',CASES)
def test_crossing_a_complete_piece_blocks_atomically_but_another_clear_axis_can_turn(kind,factory):
    cube=factory().apply_move(Move(0,0,JUMBLE));before=cube.signature()
    assert not cube.can_apply(Move(1,0,180.))
    with pytest.raises(ValueError,match='rigid.blocked'):cube.apply_move(Move(1,0,180.))
    assert cube.signature()==before
    # This is an independent physical cut, not merely undoing the first axis.
    second=Move(3,0,JUMBLE);members=cube.selection(3)
    assert members and cube.can_apply(second)
    cube.apply_move(second);assert cube.signature()!=before
    cube.apply_move(Move(3,0,-JUMBLE));assert cube.signature()==before


def test_twins_uses_union_of_atoms_and_supports_its_second_preparation_angle():
    from cube.cad_copter_clearance import regions,side
    from cube.spherical_cells import Plane
    cut=Plane((1.,0.,0.),0.)
    for h,atoms in enumerate(regions('twins')):
        values={a.side(cut) for a in atoms}
        if values=={-1,1}:
            assert side('twins',h,cut)==0;break
    else:pytest.fail('Expected a whole CSG piece spanning two individually clear atoms')
    cube=TwinsState();before=cube.signature()
    cube.apply_move(Move(0,0,SECOND))
    assert any(abs(v)>1.01 for p in cube.world_panels() for q in p for v in q)
    assert any(1e-5<abs(v)<1-1e-5 for f in cube.frames for col in f for v in col)
    cube.apply_move(Move(0,0,-SECOND));assert cube.signature()==before


@pytest.mark.parametrize('kind,factory',CASES)
def test_cancellation_and_failed_repairs_preserve_every_piece_and_paint(kind,factory):
    cube=factory().apply_move(Move(0,0,JUMBLE));before=cube.signature();calls=[]
    def cancel_gate():
        calls.append(1)
        if len(calls)==3:raise InterruptedError()
    with pytest.raises(InterruptedError):cube.apply_move(Move(3,0,JUMBLE),cancel_gate)
    assert cube.signature()==before
    from importlib import import_module
    solver=import_module('solver.flower_copter' if kind=='flower' else 'solver.twins')
    with pytest.raises(InterruptedError):solver.solve(cube,cancel=lambda:True)
    with pytest.raises(TimeoutError):solver.solve(cube,seconds=0.)
    assert cube.signature()==before


@pytest.mark.parametrize('kind,factory',CASES)
@pytest.mark.parametrize('seed',range(6))
@pytest.mark.parametrize('length',(30,100))
def test_shape_scramble_session_reentry_and_full_solve_without_a_move_history(kind,factory,seed,length):
    from importlib import import_module
    model=import_module('cube.flower_copter_aligned' if kind=='flower' else 'cube.twins_aligned')
    solver=import_module('solver.flower_copter' if kind=='flower' else 'solver.twins')
    source=model.scrambled(seed,length,**({'shape':True} if kind=='flower' else {'jumble':True}))
    assert any(abs(v)>1.01 for p in source.world_panels() for q in p for v in q)
    from renderer.cad_copter_visibility import basis
    assert len({basis(f)[0] for f in source.frames})>1  # Not a rigidly rotated whole cube.
    from app.session import encode,decode
    cube=decode(json.loads(json.dumps(encode(source))))
    cube=factory.from_observation(json.loads(json.dumps(cube.observation_data())))
    assert not hasattr(cube,'history') and cube.signature()==source.signature()
    before=cube.signature();word=solver.solve(cube,seconds=30.)
    # Replay every returned action through the same exact native solid gates.
    assert cube.clone().apply_moves(word).is_solved()
    assert cube.signature()==before and cube.paints==source.paints


@pytest.mark.parametrize('kind,factory',CASES)
def test_shape_render_keeps_all_coloured_fields_and_exposed_plastic_during_the_next_turn(kind,factory):
    if kind=='flower':
        from renderer.flower_copter_view import FlowerCopterView as View
        view=SimpleNamespace(_move=None,piece_filter=None,outer_skin=View.outer_skin,
                             home_surfaces=View.home_surfaces,skin=View.skin)
    else:
        from renderer.twins_cad_view import TwinsCADView as View
        view=SimpleNamespace(_move=None,piece_filter=None)
    cube=factory().apply_move(Move(0,0,JUMBLE));rest=View._surfaces(view,cube)
    assert {r[3] for r in rest if r[3] is not None}==set(range(len(cube.panels)))
    assert any(r[3] is None for r in rest)
    view._move=Move(3,0,180.)
    moving=View._surfaces(view,cube)
    assert {r[3] for r in moving if r[3] is not None}==set(range(len(cube.panels)))
    assert {r for r in rest if r[3] is None}<={r for r in moving if r[3] is None}


@pytest.mark.parametrize('kind,factory',CASES)
def test_visibility_recognizes_cubic_reorientations_of_neighbours_and_retains_open_interfaces(kind,factory):
    from importlib import import_module
    from renderer.cad_copter_visibility import visible_cuts
    model=import_module('cube.flower_copter_aligned' if kind=='flower' else 'cube.twins_aligned')
    skin=import_module('renderer.flower_copter_view' if kind=='flower' else 'renderer.twins_cad_view').skin_data
    cube=model.scrambled(13,100);rows,ids=skin();visible=visible_cuts(cube,kind)
    def count():
        return sum(slot<0 and a in visible[h] for h,row in enumerate(rows)
                   for (tri,n,slot),a in zip(row,ids[h]))
    assert count()==0  # Different local frames still fit in one closed shell.
    cube.apply_move(Move(0,0,JUMBLE));visible=visible_cuts(cube,kind)
    assert 0<count()<sum(map(len,rows))/4


@pytest.mark.parametrize('kind,factory',CASES)
def test_play_controls_offer_shape_angles_without_restoring_manual_input(kind,factory):
    if kind=='flower':
        from ui.screens.flower_copter_screen import FlowerCopterTwistScreen as Screen,FlowerCopterInputScreen as Entry
        from renderer.flower_copter_view import FlowerCopterTwistView as View
    else:
        from ui.screens.twins_screen import TwinsTwistScreen as Screen,TwinsInputScreen as Entry
        from renderer.twins_cad_view import TwinsCADTwistView as View
    from ui.screens.copter_screen import PLAY_ONLY_KINDS
    assert factory.puzzle_kind in PLAY_ONLY_KINDS
    for axis in (0,12):
        screen=SimpleNamespace(_axis=axis,layer=SimpleNamespace(),view=SimpleNamespace())
        screen._layer_selected=lambda widget,text:Screen._layer_selected(screen,widget,text)
        Screen._set_layers(screen)
        assert not screen.layer.disabled
        for index,angle in enumerate(screen._angles):
            Screen._layer_selected(screen,screen.layer,screen.layer.values[index])
            assert View.amount_for_axis(screen.view,axis)==angle
            assert factory().can_apply(Move(axis,0,angle))
    cube=Entry.make_scrambled(seed=17,length=30)
    assert any(abs(v)>1.01 for p in cube.world_panels() for q in p for v in q)
