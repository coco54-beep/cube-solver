"""The photographed YJ Ivy ball, including spherical picking and manual input."""
import math
import pytest
from cube.polyhedral import PolyhedralPuzzle,Move,dot,rotate


def test_ball_keeps_ivy_piece_actions_without_a_cube_shaped_shell():
    from renderer.yeet_ball_mesh import skin,edge,RADIUS,point
    ball=PolyhedralPuzzle('yeet_ball',3);ivy=PolyhedralPuzzle('ivy',3)
    g=ball.geometry
    assert ball.puzzle_kind=='yeet_ball' and g.spec.kind=='yeet_ball'
    assert len(g.pieces)==10 and len(g.stickers)==18 and len(g.spec.axes)==4
    assert sorted(map(len,g.pieces))==[1]*6+[3]*4
    assert g.permutations==ivy.geometry.permutations
    patches=skin();assert len(patches)==18
    assert 1000<sum(map(len,patches))<5000
    area=solid_angle=0
    from cube.polyhedral import cross,add,scale,unit
    for part in patches:
        for triangle,normal,normals in part:
            assert all(abs(dot(v,v)-RADIUS**2)<1e-10 for v in triangle)
            assert dot(normal,tuple(sum(p[i] for p in triangle)/3 for i in range(3)))>0
            a,b,c=triangle;cr=cross(add(b,scale(a,-1)),add(c,scale(a,-1)))
            area+=math.sqrt(dot(cr,cr))/2
            a,b,c=unit(a),unit(b),unit(c)
            solid_angle+=2*math.atan2(abs(dot(a,cross(b,c))),1+dot(a,b)+dot(b,c)+dot(c,a))
    # Radial triangles cover the sphere exactly; the low-cost flat GPU mesh
    # approximates its curved area within half a percent at mobile resolution.
    assert abs(solid_angle-4*math.pi)<1e-8
    assert abs(area/(4*math.pi*RADIUS**2)-1)<.005
    for move in ball.moves():
        turn=2*math.pi/3;axis=g.spec.axes[move.axis]
        for s in g.stickers:
            p=s.polygon[0]
            assert max(abs(a-b) for a,b in zip(point(rotate(p,axis,turn)),rotate(point(p),axis,turn)))<1e-10
        work=ball.clone()
        for _ in range(3):work.apply_move(move)
        assert work.colors==ball.colors


@pytest.mark.parametrize('seed',range(12))
@pytest.mark.parametrize('length',(30,100))
def test_observed_ball_scrambles_reenter_and_solve_without_history(seed,length):
    from cube.polyhedral_scramble import scramble
    from services.solve_service import SolveService,CancelToken
    from services.solution_cache import clear
    source=PolyhedralPuzzle('yeet_ball',3);scramble(source,length,20261026+seed)
    entered=PolyhedralPuzzle('yeet_ball',3,[-1]*18)
    for i,c in enumerate(source.colors):entered.colors[i]=c
    original=tuple(entered.colors);answers=[];clear()
    SolveService()._run(entered,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success
    assert len(answers[0].moves)<=12
    replay=entered.entered()
    for move in answers[0].moves:replay.apply_move(move)
    assert replay.is_solved()
    assert tuple(entered.colors)==original and not entered.scramble_history
    clear()


def test_ball_input_rejects_impossible_counts_and_mirrored_corner():
    from cube.yeet_ball import solve
    c=PolyhedralPuzzle('yeet_ball',3);c.colors[0]=-1
    with pytest.raises(ValueError):solve(c)
    c=PolyhedralPuzzle('yeet_ball',3)
    slots=next(p for p in c.geometry.pieces if len(p)==3)
    a,b=slots[:2];c.colors[a],c.colors[b]=c.colors[b],c.colors[a]
    with pytest.raises(ValueError):solve(c)
    with pytest.raises(InterruptedError):solve(c,cancel=lambda:True)


def test_entered_spherical_state_survives_a_json_checkpoint_without_history():
    import json
    from app.session import encode,decode
    from cube.polyhedral_scramble import scramble
    source=PolyhedralPuzzle('yeet_ball',3);scramble(source,100,20261026)
    entered=source.entered();entered.colors[5]=-1
    restored=decode(json.loads(json.dumps(encode(entered))))
    assert restored.puzzle_kind=='yeet_ball' and restored.colors==entered.colors
    assert restored.geometry.spec.kind=='yeet_ball' and not restored.scramble_history


def test_ball_has_one_existing_family_and_original_real_model_examples():
    from candidate_puzzles import CATALOGUE_FAMILIES,catalogue_family
    from demo.expanded_tutorials import lessons
    from demo.expanded_support import make_cube
    assert catalogue_family('yeet_ball')=='ivy_family'
    assert sum('yeet_ball' in models for models in CATALOGUE_FAMILIES.values())==1
    for step in lessons('yeet_ball',3):
        for case in step['cases']:
            work=case['initial'].entered();assert work.puzzle_kind=='yeet_ball'
            for move in case['moves']:work.apply_move(move)
            assert work.is_solved()


def test_ivy_commutator_cycles_only_three_leaves():
    from solver.polyhedral import apply_word
    c=PolyhedralPuzzle('yeet_ball',3);g=c.geometry
    word=(Move(0),Move(1),Move(0,0,2),Move(1,0,2))
    effect=apply_word(g,word)
    moved=[p for p,slots in enumerate(g.pieces) if any(effect[i]!=i for i in slots)]
    assert len(moved)==3 and all(len(g.pieces[p])==1 for p in moved)
    replay=c.clone()
    for _ in range(3):
        for move in word:replay.apply_move(move)
    assert replay.is_solved()
