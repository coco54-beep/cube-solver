import json
import pytest
from cube.edge_jumbling import scrambled
from cube.spherical_jumbling import FACTORIES
from cube.polyhedral import Move
from cube.curvy_copter import JUMBLE
from app.session import encode,decode


def test_bauhinia_preparation_opens_an_overlapping_cap_not_only_a_disjoint_turn():
    from cube.spherical_jumbling import BauhiniaCube,BAU_JUMBLE
    c=BauhiniaCube();members=set(c.selection(0));c.apply_move(Move(0,0,BAU_JUMBLE))
    opened=[]
    for axis in range(1,20):
        try:selected=set(c.selection(axis))
        except ValueError:continue
        if selected&members:opened.append(axis)
    assert opened
    c.apply_move(Move(opened[0],0,120.))


@pytest.mark.parametrize('kind',('clover','mf8_bauhinia_minx'))
def test_cached_spherical_skin_preserves_every_painted_patch_and_exposed_plastic(kind):
    from renderer.edge_jumbling_view import placed_spheres
    from cube.spherical_jumbling import BAU_JUMBLE
    from types import SimpleNamespace
    c=FACTORIES[kind]();v=SimpleNamespace(_move=None,piece_filter=None)
    closed=placed_spheres(v,c)
    assert all(row[3] is not None for row in closed)
    c.apply_move(Move(0,0,BAU_JUMBLE if kind=='mf8_bauhinia_minx' else JUMBLE))
    rows=placed_spheres(v,c)
    assert {r[3] for r in rows if r[3] is not None}==set(range(len(c.panels)))
    assert any(r[3] is None for r in rows)


@pytest.mark.parametrize('kind',tuple(FACTORIES))
def test_whole_material_turns_block_and_reverse_without_paint_loss(kind):
    from cube.spherical_jumbling import BAU_JUMBLE
    c=FACTORIES[kind]();before=c.signature();angle=BAU_JUMBLE if kind=='mf8_bauhinia_minx' else JUMBLE
    assert c.is_solved();c.apply_move(Move(0,0,angle));assert c.signature()!=before
    blocked=[a for a in range(len(c.turn_axes)) if not c.can_apply(Move(a,0,c.turn_steps[a]))]
    assert blocked
    shaped=c.signature()
    with pytest.raises(ValueError):c.apply_move(Move(blocked[0],0,c.turn_steps[blocked[0]]))
    assert c.signature()==shaped and c.paints==FACTORIES[kind]().paints
    c.apply_move(Move(0,0,-angle));assert c.signature()==before


@pytest.mark.parametrize('kind',tuple(FACTORIES))
@pytest.mark.parametrize('seed',range(3))
@pytest.mark.parametrize('length',(30,100))
def test_independent_state_reentry_solve_and_native_replay(kind,seed,length):
    from solver.edge_jumbling import solve
    source=scrambled(kind,seed,length)
    c=type(source).from_observation(json.loads(json.dumps(source.observation_data())))
    c=decode(json.loads(json.dumps(encode(c))));before=c.signature()
    word=solve(c,seconds=45)
    assert c.clone().apply_moves(word).is_solved() and c.signature()==before
    assert not getattr(c,'history',None)


@pytest.mark.parametrize('kind', ('helicopter', 'clover'))
@pytest.mark.parametrize('seed', range(3))
def test_play_and_resume_solve_the_legal_jumble_that_crosses_regular_orbits(kind, seed):
    from cube.copter_aligned import inverse_word
    from services.solve_service import CancelToken, SolveService

    source = scrambled(kind, seed, 20)
    # Every deformation step must be recorded, including the optional second turn.
    assert source.clone().apply_moves(inverse_word(source.history)).is_solved()
    live = FACTORIES[kind]()
    live.restore(source)
    live.apply_moves(inverse_word(source.history[20:]))
    live.apply_moves((Move(1, 0, JUMBLE), Move(6, 0, JUMBLE), Move(0, 0, 180),
                      Move(6, 0, -JUMBLE), Move(1, 0, -JUMBLE)))
    live.aligned_permutation()
    restored = decode(json.loads(json.dumps(encode(live)))).entered()
    before = restored.signature()
    answers = []
    SolveService()._run(restored, answers.append, None, CancelToken())
    answer, = answers
    assert answer.success, answer.message
    assert restored.clone().apply_moves(answer.moves).is_solved()
    assert restored.signature() == before


@pytest.mark.parametrize('kind',tuple(FACTORIES))
def test_cancel_is_atomic_and_routes_use_full_material(kind):
    from app.application import CubeApp
    from types import SimpleNamespace
    from ui.screens.polyhedral_screen import _entry_for,_view_for
    from renderer.edge_jumbling_view import EdgeJumblingView,EdgeJumblingTwistView
    app=SimpleNamespace();CubeApp.new_polyhedral(app,kind,3)
    assert type(app.cube) is FACTORIES[kind] and app.cube.is_solved()
    assert _entry_for(app.cube)=='EdgeJumblingInputScreen'
    assert _view_for(app.cube) is EdgeJumblingView and _view_for(app.cube,True) is EdgeJumblingTwistView
    before=app.cube.signature()
    def guard():raise InterruptedError()
    with pytest.raises(InterruptedError):app.cube.apply_move(Move(0,0,app.cube.turn_steps[0]),guard)
    assert app.cube.signature()==before
