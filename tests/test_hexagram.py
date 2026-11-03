"""The rounded tetrahedron has independent cells, paint fields and solver data."""
from collections import Counter
import json
import pytest
from cube.hexagram import HexagramCube,structure
from cube.hexagram_aligned import scrambled,generators,observed_colors,AlignedHexagram
from cube.pisces import ANGLE1
from cube.polyhedral import Move,key


def test_rounded_housing_is_closed_and_not_a_reskin_of_the_six_coloured_pisces_fields():
    from cube.crazy_comet import volume
    from renderer.pisces_view import hexagram_surfaces,hexagram_outlines
    c=HexagramCube();assert len(c.solids)==35 and len(c.panels)==64
    assert Counter(f for h,f,p in c.panels)=={i:16 for i in range(4)}
    assert Counter(Counter(h for h,f,p in c.panels).values())=={1:12,2:18,3:4,4:1}
    for solid in c.solids:
        assert volume(solid)>1e-11
        edges=Counter(tuple(sorted((key(a),key(b)))) for p,f in solid for a,b in zip(p,p[1:]+p[:1]))
        assert set(edges.values())=={2}
    assert {slot for row in hexagram_surfaces() for tri,n,slot in row if slot>=0}==set(range(64))
    assert set(hexagram_outlines())==set(range(64))


@pytest.mark.parametrize('axis',range(12))
def test_offset_axes_reverse_all_material_and_refuse_blocked_turns_without_mutation(axis):
    c=HexagramCube();before=c.signature();c.apply_move(Move(axis,0,ANGLE1))
    bad=next(m for m in c.moves() if not c.can_apply(m));changed=c.signature()
    with pytest.raises(ValueError,match='rigid.blocked'):c.apply_move(bad)
    assert c.signature()==changed
    c.apply_move(Move(axis,0,-ANGLE1));assert c.signature()==before


def test_closed_tools_and_every_compiled_transversal_replay_the_tetrahedral_model():
    from solver.hexagram import _profile
    from solver.polyhedral import apply_word
    rows=generators();assert len(rows)==28
    for action,word in rows:
        work=HexagramCube().apply_moves(word);assert work.aligned_permutation()==action
        work.apply_moves(tuple(Move(m.axis,0,-m.amount) for m in reversed(word)));assert work.is_solved()
    data=_profile.data();assert data['verified_transversals']==132
    g=AlignedHexagram().geometry
    for row in data['transversals']:
        for record in row.values():assert apply_word(g,tuple(Move(*m) for m in record['word']))==tuple(record['permutation'])


@pytest.mark.parametrize('seed',range(3))
@pytest.mark.parametrize('length',(30,100))
def test_independent_pose_colour_and_colour_only_reentry_solve_without_a_move_log(seed,length):
    from solver.hexagram import solve
    from app.session import encode,decode
    source=scrambled(seed,length);entered=HexagramCube.from_observation(json.loads(json.dumps(source.observation_data())))
    before=entered.signature();assert decode(json.loads(json.dumps(encode(entered)))).signature()==before
    word=solve(entered,seconds=15);assert source.clone().apply_moves(word).is_solved() and entered.signature()==before
    flat=scrambled(seed,length,jumble=False);entered=HexagramCube(paints=observed_colors(flat))
    word=solve(entered,seconds=15);assert entered.clone().apply_moves(word).is_solved()


def test_cancel_and_incomplete_entry_keep_all_four_colour_fields_and_poses():
    from solver.hexagram import solve
    c=scrambled(31);before=c.signature()
    with pytest.raises(InterruptedError):solve(c,cancel=lambda:True)
    assert c.signature()==before
    c.paint(0,-1);before=c.signature()
    with pytest.raises(ValueError,match='every sticker'):solve(c)
    assert c.signature()==before


def test_existing_tetrahedral_category_public_routes_and_original_lessons():
    from candidate_puzzles import CATALOGUE_FAMILIES,catalogue_family
    from demo.expanded_support import make_cube,view_class,entry_screen
    from ui.screens.polyhedral_screen import _entry_for,_view_for
    from demo.expanded_tutorials import lessons
    c=make_cube('lanlan_hexagram',3)
    assert catalogue_family(c.puzzle_kind)=='pyraminx'
    assert sum(c.puzzle_kind in rows for rows in CATALOGUE_FAMILIES.values())==1
    assert entry_screen(c.puzzle_kind)==_entry_for(c)=='HexagramInputScreen'
    assert view_class(c.puzzle_kind) is _view_for(c)
    for lesson in lessons(c.puzzle_kind,3):
        for case in lesson['cases']:assert case['initial'].clone().apply_moves(case['moves']).is_solved()


def test_precomputed_housing_and_active_solver_assets_are_included_by_both_packagers():
    from scripts.bundle_assets import audit,windows_assets,ROOT
    selected={p.relative_to(ROOT).as_posix() for p in windows_assets()}
    assert {'cube/data/pillowed_tetra_shell.bin','solver/data/hexagram_colour_group.bin'}<=selected
    assert audit()['windows_asset_bytes']>0


@pytest.mark.parametrize('seed',(1,2))
def test_hundred_primitive_turn_reentry_can_continue_beyond_the_old_eight_level_stop(seed):
    from random import Random
    from solver.hexagram import solve
    rng=Random(seed);source=HexagramCube();previous=-1
    for _ in range(100):
        choices=list(source.moves());rng.shuffle(choices);choices.sort(key=lambda m:m.axis==previous)
        for move in choices:
            if source.can_apply(move):source.apply_move(move);previous=move.axis;break
        else:raise AssertionError('No legal continuation')
    entered=HexagramCube.from_observation(json.loads(json.dumps(source.observation_data())))
    before=entered.signature();word=solve(entered,seconds=15)
    assert entered.signature()==before and entered.clone().apply_moves(word).is_solved()
