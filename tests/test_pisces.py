"""Whole Pisces solids, grouped paint patches and independent state entry."""
from collections import Counter
import json
import pytest
from cube.pisces import PiscesCube,ANGLE1,ANGLE2,AXES
from cube.pisces_aligned import scrambled,generators,observed_colors,AlignedPisces
from cube.polyhedral import Move,key
from candidate_puzzles import BY_KIND


def test_closed_cells_and_photographed_piece_classes_do_not_count_mesh_facets_as_fields():
    from cube.crazy_comet import volume
    from renderer.pisces_view import surfaces,outlines
    c=PiscesCube();counts=Counter(h for h,f,p in c.panels)
    assert len(c.solids)==35 and len(c.panels)==60
    assert Counter(counts.values())=={1:18,2:12,3:4,6:1}
    assert Counter(f for h,f,p in c.panels)=={i:10 for i in range(6)}
    for solid in c.solids:
        assert volume(solid)>1e-11
        edges=Counter(tuple(sorted((key(a),key(b)))) for poly,f in solid for a,b in zip(poly,poly[1:]+poly[:1]))
        assert set(edges.values())=={2}
    assert len({slot for row in surfaces() for tri,n,slot in row if slot>=0})==60
    assert set(outlines())==set(range(60)) and all(outlines().values())


@pytest.mark.parametrize('axis',range(12))
def test_real_degrees_move_complete_material_reverse_and_refuse_blocked_cuts_atomically(axis):
    c=PiscesCube();before=c.signature();paint=c.paints
    c.apply_move(Move(axis,0,ANGLE1));assert c.signature()!=before and c.paints==paint
    bad=next(m for m in c.moves() if not c.can_apply(m));changed=c.signature()
    with pytest.raises(ValueError,match='rigid.blocked'):c.apply_move(bad)
    assert c.signature()==changed
    c.apply_move(Move(axis,0,-ANGLE1));assert c.signature()==before


def test_every_closed_circuit_is_a_guarded_whole_piece_permutation_and_matches_its_compiled_asset():
    from solver.pisces import _profile
    from solver.polyhedral import apply_word
    rows=generators();assert len(rows)==28
    for action,word in rows:
        c=PiscesCube().apply_moves(word);assert c.aligned_permutation()==action
        c.apply_moves(tuple(Move(m.axis,0,-m.amount) for m in reversed(word)));assert c.is_solved()
    data=_profile.data();assert data['verified_transversals']==109
    g=AlignedPisces().geometry
    for row in data['transversals']:
        for record in row.values():assert apply_word(g,tuple(Move(*m) for m in record['word']))==tuple(record['permutation'])


@pytest.mark.parametrize('seed',range(3))
@pytest.mark.parametrize('length',(30,100))
def test_colour_only_and_partial_shape_observation_reentry_solve_without_history(seed,length):
    from solver.pisces import solve
    from app.session import encode,decode
    source=scrambled(seed,length);entered=PiscesCube.from_observation(json.loads(json.dumps(source.observation_data())))
    before=entered.signature();restored=decode(json.loads(json.dumps(encode(entered))))
    assert restored.signature()==before
    word=solve(entered,seconds=15)
    assert entered.clone().apply_moves(word).is_solved() and entered.signature()==before
    flat=scrambled(seed,length,jumble=False);entered=PiscesCube(paints=observed_colors(flat))
    word=solve(entered,seconds=15);assert entered.clone().apply_moves(word).is_solved()


@pytest.mark.parametrize('seed',range(3))
def test_raw_thirty_primitive_turn_observation_uses_no_recorded_moves(seed):
    from random import Random
    from solver.pisces import solve
    rng=Random(seed);source=PiscesCube();previous=-1
    for _ in range(30):
        choices=[m for m in source.moves() if m.axis!=previous];rng.shuffle(choices)
        for m in choices:
            if source.can_apply(m):source.apply_move(m);previous=m.axis;break
        else:raise AssertionError('No independent next axis')
    entered=PiscesCube.from_observation(json.loads(json.dumps(source.observation_data())))
    word=solve(entered,seconds=15);assert source.clone().apply_moves(word).is_solved()


def test_fixed_six_face_core_has_valid_identity_mapping_and_rejects_wrong_centre_colours():
    from cube.rigid_placements import placements
    from solver.pisces import validate
    c=PiscesCube();home=next(h for h,s in enumerate(c.geometry.pieces) if len(s)==6)
    assert len(placements(PiscesCube,home)[0][2])==6
    validate(c.paints);a,b=c.geometry.pieces[home][:2];paint=list(c.paints);paint[a],paint[b]=paint[b],paint[a]
    with pytest.raises(ValueError):validate(paint)
    from cube.appearance import ROTATIONS,IDENTITY_FRAME
    from solver.pisces import solve
    from services.failures import classify
    c.set_piece_frame(home,next(f for f in ROTATIONS if f!=IDENTITY_FRAME));before=c.signature()
    with pytest.raises(ValueError,match='tilted.fixed_core') as caught:solve(c)
    assert classify(exception=caught.value)=='illegal' and len(caught.value.locations)==6
    assert c.signature()==before


def test_pose_full_circle_failures_and_cancellation_keep_input():
    from cube.appearance import IDENTITY_FRAME
    from cube.curvy_copter import multiply
    from cube.polyhedral import rotate
    from solver.pisces import solve
    import math
    c=scrambled(52);before=c.signature();home=c.panels[-1][0]
    turn=tuple(rotate(p,(0.,1.,0.),math.pi/2) for p in IDENTITY_FRAME)
    for _ in range(4):c.set_piece_frame(home,multiply(turn,c.frames[home]))
    assert c.signature()==before
    with pytest.raises(InterruptedError):solve(c,cancel=lambda:True)
    assert c.signature()==before
    c.paint(0,-1);before=c.signature()
    with pytest.raises(ValueError,match='every sticker'):solve(c)
    assert c.signature()==before


@pytest.mark.skipif('lanlan_pisces' not in BY_KIND, reason='Pisces removed from catalogue')
def test_single_directory_home_public_entry_twist_replay_and_original_lessons():
    from candidate_puzzles import CATALOGUE_FAMILIES
    from demo.expanded_support import make_cube,view_class,entry_screen
    from ui.screens.polyhedral_screen import _view_for,_entry_for
    from demo.expanded_tutorials import lessons
    c=make_cube('lanlan_pisces',3)
    assert sum(c.puzzle_kind in rows for rows in CATALOGUE_FAMILIES.values())==1
    assert entry_screen(c.puzzle_kind)==_entry_for(c)=='PiscesInputScreen'
    assert view_class(c.puzzle_kind) is _view_for(c)
    for lesson in lessons(c.puzzle_kind,3):
        for case in lesson['cases']:assert case['initial'].clone().apply_moves(case['moves']).is_solved()
