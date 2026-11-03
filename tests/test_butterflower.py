"""Radius-one cut topology, the two confirmed moves and independent input."""
from collections import Counter
import math
import pytest
from cube.butterflower import ButterflowerCube
from cube.butterflower_material import cuts,structure
from cube.butterflower_aligned import scrambled,observed_colors,AlignedButterflower
from cube.polyhedral import Move,dot,cross


def test_radius_one_is_an_independent_material_not_the_deeper_flower():
    from cube.flower_material import cuts as flower_cuts
    from renderer.butterflower_view import surfaces
    c=ButterflowerCube()
    assert all(s.radius==1. for s in cuts()) and cuts()!=flower_cuts()
    assert len(c.regions)==101 and len(c.panels)==120
    assert Counter(Counter(h for h,f,p in c.panels).values())=={1:48,2:36}
    assert Counter(f for h,f,p in c.panels)=={f:20 for f in range(6)}
    for face in range(6):
        normal=c.geometry.spec.normals[face]
        area=sum(abs(sum(dot(cross(a,b),normal) for a,b in zip(p,p[1:]+p[:1])))/2 for h,f,p in c.panels if f==face)
        assert math.isclose(area,4.,abs_tol=1e-7)
    assert {slot for row in surfaces() for tri,n,slot in row if slot>=0}==set(range(120))


@pytest.mark.parametrize('axis',range(20))
def test_the_confirmed_edge_and_corner_turns_close_every_material_cell(axis):
    c=ButterflowerCube();before=c.signature();step=180. if axis<12 else 120.
    c.apply_move(Move(axis,0,step));c.validate_pose()
    assert sorted(c.aligned_permutation())==list(range(120))
    c.apply_move(Move(axis,0,-step));assert c.signature()==before
    for _ in range(2 if axis<12 else 3):c.apply_move(Move(axis,0,step))
    assert c.signature()==before


def test_regular_edge_and_corner_positions_need_no_extra_preparation_move():
    c=scrambled(31,100,shape=False)
    assert c.turn_steps==(180,)*12+(120,)*8
    for move in (Move(a,0,180. if a<12 else 120.) for a in range(20)):
        assert c.can_apply(move)
        c.clone().apply_move(move).validate_pose()


@pytest.mark.parametrize('length',(30,100,300))
@pytest.mark.parametrize('seed',range(3))
def test_manual_face_colour_input_solves_without_scramble_history(seed,length):
    from solver.butterflower import solve
    source=scrambled(seed,length,shape=False);visible=observed_colors(source)
    entered=ButterflowerCube(paints=(-1,)*120)
    for face in range(6):
        for i,(h,f,p) in enumerate(entered.panels):
            if f==face:entered.paint(i,visible[i])
    before=entered.signature();word=solve(entered,seconds=10)
    assert entered.signature()==before and entered.clone().apply_moves(word).is_solved()


def test_certificate_and_session_replay_are_profile_specific():
    from solver.butterflower import _profile
    from solver.polyhedral import apply_word
    from app.session import encode,decode
    from cube.butterflower_aligned import expand
    data=_profile.data();g=AlignedButterflower().geometry
    for row in data['transversals']:
        for record in row.values():
            word=tuple(Move(*m) for m in record['word'])
            assert apply_word(g,word)==tuple(record['permutation'])
    c=scrambled(6,30);copy=decode(encode(c))
    assert type(copy) is ButterflowerCube and copy.signature()==c.signature()
    from cube.flower_copter import FlowerCopterCube
    with pytest.raises(ValueError):FlowerCopterCube.from_observation(c.observation_data())


def test_service_and_cancel_preserve_the_entered_state():
    from services.solve_service import SolveService,CancelToken
    from solver.butterflower import solve
    c=ButterflowerCube(paints=observed_colors(scrambled(7,30,shape=False)));before=c.signature();answers=[]
    with pytest.raises(InterruptedError):solve(c,cancel=lambda:True)
    assert c.signature()==before
    SolveService()._run(c,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success
    assert c.signature()==before and c.clone().apply_moves(answers[0].moves).is_solved()


def test_exact_alignment_unlocks_adjacent_edge_but_estimated_120_does_not():
    from cube.butterflower import JUMBLE
    root=ButterflowerCube()
    candidate=root.clone().apply_move(Move(0,0,JUMBLE))
    assert candidate.can_apply(Move(3,0,JUMBLE))
    assert candidate.can_apply(Move(4,0,JUMBLE))
    estimated=root.clone().apply_move(Move(0,0,120.));before=estimated.signature()
    with pytest.raises(ValueError,match='rigid.blocked'):estimated.apply_move(Move(3,0,180.))
    assert estimated.signature()==before
    supplementary=root.clone().apply_move(Move(0,0,180.-JUMBLE))
    assert supplementary.can_apply(Move(1,0,JUMBLE))


def test_every_compiled_petal_exchange_closes_and_double_replays_all_material():
    from cube.butterflower_aligned import generators
    root=ButterflowerCube();rows=generators()
    assert len(rows)==44
    for action,word in rows[20:]:
        work=root.clone().apply_moves(word)
        assert work.aligned_permutation()==action and sum(a!=i for i,a in enumerate(action))==14
        assert work.apply_moves(word).signature()==root.signature()


@pytest.mark.parametrize('length',(30,100,300))
@pytest.mark.parametrize('seed',range(4))
def test_visible_only_manual_shape_is_completed_and_solved_without_history(seed,length):
    from solver.butterflower import prepare_observation,solve
    from cube.appearance import IDENTITY_FRAME
    from app.session import encode,decode
    source=scrambled(seed,length);visible={h for h,f,p in source.panels}
    entered=ButterflowerCube(tuple(f if h in visible else IDENTITY_FRAME for h,f in enumerate(source.frames)),(-1,)*120)
    for i,color in enumerate(source.paints):entered.paint(i,color)
    entered=decode(encode(entered));before=entered.signature()
    ready=prepare_observation(entered,seconds=10)
    assert entered.signature()==before and ready.paints==entered.paints
    for h in visible:
        assert all(abs(a-b)<1e-7 for u,v in zip(entered.frames[h],ready.frames[h]) for a,b in zip(u,v))
    word=solve(ready,seconds=10)
    assert ready.clone().apply_moves(word).is_solved()


def test_visible_completion_cancellation_timeout_and_service_playback():
    from solver.butterflower import prepare_observation
    from cube.appearance import IDENTITY_FRAME
    from services.solve_service import SolveService,CancelToken
    source=scrambled(17,30);visible={h for h,f,p in source.panels}
    entered=ButterflowerCube(tuple(f if h in visible else IDENTITY_FRAME for h,f in enumerate(source.frames)),source.paints)
    before=entered.signature()
    with pytest.raises(InterruptedError):prepare_observation(entered,lambda:True)
    with pytest.raises(TimeoutError):prepare_observation(entered,seconds=0)
    assert entered.signature()==before
    results=[];SolveService()._run(entered,results.append,None,CancelToken())
    result,=results
    assert result.success and result.prepared_cube is not None and entered.signature()==before
    assert result.prepared_cube.clone().apply_moves(result.moves).is_solved()
    entered.paint(0,-1);incomplete=entered.signature();results=[]
    SolveService()._run(entered,results.append,None,CancelToken())
    assert not results[0].success and results[0].failure_category=='incomplete'
    assert entered.signature()==incomplete


def test_jumbled_camera_layer_and_plastic_surfaces_match_legal_turns():
    from renderer.butterflower_view import ButterflowerView,ButterflowerTwistView
    from renderer.flower_copter_view import FlowerCopterView
    from renderer.camera_follow import polyhedral_target
    from types import SimpleNamespace
    c=scrambled(23,30);move=next(m for m in c.moves() if c.can_apply(m))
    assert c.geometry.layers[move.axis][0]==c.selection(move.axis)
    assert all(math.isfinite(v) for v in polyhedral_target(c,move))
    view=SimpleNamespace(_move=move,piece_filter=None,outer_skin=ButterflowerView.outer_skin,
        home_surfaces=ButterflowerView.home_surfaces,skin=ButterflowerView.skin)
    records=FlowerCopterView._surfaces(view,c)
    assert records and any(r[2]==-1 for r in records)
    assert {r[3] for r in records if r[3] is not None}==set(range(120))
    assert ButterflowerTwistView.amount_for_axis(SimpleNamespace(turn_amount=70.528),0)==70.528
    assert ButterflowerTwistView.amount_for_axis(SimpleNamespace(turn_amount=70.528),12)==120.
