"""Research material invariants; this does not approve the physical shell."""
from collections import Counter
import json
import pytest
from cube.clover_pyraminx import CloverPyraminxCube,structure
from cube.clover_pyraminx_aligned import scrambled,generators,observed_colors,AlignedCloverPyraminx
from cube.pisces import ANGLE1
from cube.polyhedral import Move,key


def test_rounded_housing_is_closed_and_not_a_reskin_of_the_six_coloured_pisces_fields():
    from cube.crazy_comet import volume
    from renderer.pisces_view import clover_pyraminx_surfaces,clover_pyraminx_outlines
    c=CloverPyraminxCube();assert len(c.solids)==31 and len(c.panels)==52
    assert Counter(f for h,f,p in c.panels)=={i:13 for i in range(4)}
    assert Counter(Counter(h for h,f,p in c.panels).values())=={1:12,2:18,4:1}
    for solid in c.solids:
        assert volume(solid)>1e-11
        edges=Counter(tuple(sorted((key(a),key(b)))) for p,f in solid for a,b in zip(p,p[1:]+p[:1]))
        assert set(edges.values())=={2}
    assert {slot for row in clover_pyraminx_surfaces() for tri,n,slot in row if slot>=0}==set(range(52))
    assert set(clover_pyraminx_outlines())==set(range(52))


@pytest.mark.parametrize('axis',range(12))
def test_offset_axes_reverse_all_material_and_refuse_blocked_turns_without_mutation(axis):
    c=CloverPyraminxCube();before=c.signature();c.apply_move(Move(axis,0,ANGLE1))
    bad=next(m for m in c.moves() if not c.can_apply(m));changed=c.signature()
    with pytest.raises(ValueError,match='rigid.blocked'):c.apply_move(bad)
    assert c.signature()==changed
    c.apply_move(Move(axis,0,-ANGLE1));assert c.signature()==before


def test_closed_tools_and_every_compiled_transversal_replay_the_tetrahedral_model():
    from solver.clover_pyraminx import _profile
    from solver.polyhedral import apply_word
    rows=generators();assert len(rows)==28
    for action,word in rows:
        work=CloverPyraminxCube().apply_moves(word);assert work.aligned_permutation()==action
        work.apply_moves(tuple(Move(m.axis,0,-m.amount) for m in reversed(word)));assert work.is_solved()
    data=_profile.data();assert data['verified_transversals']==98
    g=AlignedCloverPyraminx().geometry
    for row in data['transversals']:
        for record in row.values():assert apply_word(g,tuple(Move(*m) for m in record['word']))==tuple(record['permutation'])


@pytest.mark.parametrize('seed',range(3))
@pytest.mark.parametrize('length',(30,100))
def test_independent_pose_colour_and_colour_only_reentry_solve_without_a_move_log(seed,length):
    from solver.clover_pyraminx import solve
    from app.session import encode,decode
    source=scrambled(seed,length);entered=CloverPyraminxCube.from_observation(json.loads(json.dumps(source.observation_data())))
    before=entered.signature();assert decode(json.loads(json.dumps(encode(entered)))).signature()==before
    word=solve(entered,seconds=15);assert source.clone().apply_moves(word).is_solved() and entered.signature()==before
    flat=scrambled(seed,length,jumble=False);entered=CloverPyraminxCube(paints=observed_colors(flat))
    word=solve(entered,seconds=15);assert entered.clone().apply_moves(word).is_solved()


def test_cancel_and_incomplete_entry_keep_all_four_colour_fields_and_poses():
    from solver.clover_pyraminx import solve
    c=scrambled(31);before=c.signature()
    with pytest.raises(InterruptedError):solve(c,cancel=lambda:True)
    assert c.signature()==before
    c.paint(0,-1);before=c.signature()
    with pytest.raises(ValueError,match='every sticker'):solve(c)
    assert c.signature()==before


def test_research_workflow_is_available_to_audits_but_removed_from_catalogue():
    from candidate_puzzles import REQUESTED,CATALOGUE_FAMILIES,catalogue_family,RESEARCH_ONLY
    from demo.expanded_support import make_cube,view_class,entry_screen
    from ui.screens.polyhedral_screen import _entry_for,_view_for
    from demo.expanded_tutorials import lessons
    c=make_cube('lanlan_clover_pyraminx',3)
    from candidate_puzzles import PENDING_KINDS
    from ui.screens.irregular_directory_screen import IMPLEMENTED_ORDERS
    assert catalogue_family(c.puzzle_kind) is None
    assert all(c.puzzle_kind not in rows for rows in CATALOGUE_FAMILIES.values())
    assert c.puzzle_kind in PENDING_KINDS and c.puzzle_kind not in IMPLEMENTED_ORDERS['pyraminx']
    assert c.puzzle_kind in RESEARCH_ONLY and c.puzzle_kind not in {e.kind for e in REQUESTED}
    assert entry_screen(c.puzzle_kind)==_entry_for(c)=='CloverPyraminxInputScreen'
    assert view_class(c.puzzle_kind) is _view_for(c)
    for lesson in lessons(c.puzzle_kind,3):
        for case in lesson['cases']:assert case['initial'].clone().apply_moves(case['moves']).is_solved()


def test_research_colour_table_is_not_added_to_release_assets():
    from scripts.bundle_assets import audit,windows_assets,ROOT
    selected={p.relative_to(ROOT).as_posix() for p in windows_assets()}
    assert {'cube/data/pillowed_tetra_shell.bin','solver/data/hexagram_colour_group.bin'}<=selected
    assert not any('clover_pyraminx_colour_group.bin' in name for name in selected)
    assert audit()['windows_asset_bytes']>0


@pytest.mark.parametrize('seed',range(3))
def test_raw_primitive_walk_can_be_reentered_without_scramble_history(seed):
    from random import Random
    from solver.clover_pyraminx import solve
    rng=Random(seed);source=CloverPyraminxCube();previous=-1
    for _ in range(30):
        choices=[m for m in source.moves() if m.axis!=previous];rng.shuffle(choices)
        for m in choices:
            if source.can_apply(m):source.apply_move(m);previous=m.axis;break
        else:raise AssertionError('No legal next axis')
    entered=CloverPyraminxCube.from_observation(json.loads(json.dumps(source.observation_data())))
    before=entered.signature();word=solve(entered,seconds=15)
    assert entered.signature()==before and source.clone().apply_moves(word).is_solved()


def test_four_quarter_turn_pose_edits_restore_colours_and_solver_state():
    import math
    from cube.appearance import IDENTITY_FRAME
    from cube.curvy_copter import multiply
    from cube.polyhedral import rotate
    from solver.clover_pyraminx import solve
    c=scrambled(52);before=c.signature();home=c.panels[-1][0]
    quarter=tuple(rotate(p,(0.,1.,0.),math.pi/2) for p in IDENTITY_FRAME)
    for _ in range(4):c.set_piece_frame(home,multiply(quarter,c.frames[home]))
    assert c.signature()==before
    assert c.clone().apply_moves(solve(c,seconds=15)).is_solved()


def test_fixed_core_pose_is_not_misreported_as_a_search_timeout():
    from cube.appearance import ROTATIONS,IDENTITY_FRAME
    from solver.clover_pyraminx import solve
    from services.failures import classify
    c=CloverPyraminxCube();core=next(h for h,s in enumerate(c.geometry.pieces) if len(s)==4)
    c.set_piece_frame(core,next(f for f in ROTATIONS if f!=IDENTITY_FRAME));before=c.signature()
    with pytest.raises(ValueError,match='tilted.fixed_core') as caught:solve(c)
    assert classify(exception=caught.value)=='illegal' and len(caught.value.locations)==4
    assert c.signature()==before


@pytest.mark.parametrize('module',('pisces','hexagram','clover_pyraminx'))
def test_incomplete_certificate_does_not_claim_a_legal_puzzle_is_impossible(module,monkeypatch):
    from importlib import import_module
    from services.failures import classify
    profile=import_module('solver.'+module)._profile
    source=profile.factory().apply_moves(profile.generators()[0][1]);colours=profile.observed_colors(source)
    assert not source.is_solved()
    # Simulate an incomplete set of verified tools. This is a reachable state;
    # missing solver coverage is not evidence of a physically illegal entry.
    monkeypatch.setattr(profile,'generators',lambda:())
    with pytest.raises(ValueError,match='tilted.group_unresolved') as caught:profile.validate(colours)
    assert classify(exception=caught.value)=='timeout'


def test_exhausting_an_incomplete_colour_certificate_is_unfinished_not_illegal(monkeypatch):
    from solver.clover_pyraminx import _profile
    from services.failures import classify
    source=CloverPyraminxCube().apply_moves(generators()[0][1]);before=source.signature()
    colours=observed_colors(source);goal=tuple(f for h,f,p in source.panels)
    wrong=next(i for i,(a,b) in enumerate(zip(colours,goal)) if a!=b)
    identity=tuple(range(len(colours)))
    # A deliberately insufficient certificate must not turn a legal example
    # into an accusation of bad entry when its search runs out of choices.
    monkeypatch.setattr(_profile,'prepared',lambda:((wrong,),(((wrong,identity,()),),)))
    with pytest.raises(ValueError,match='tilted.group_unresolved') as caught:
        _profile.solve_colours(colours,seconds=5)
    assert classify(exception=caught.value)=='timeout' and source.signature()==before


@pytest.mark.parametrize('module',('pisces','hexagram','clover_pyraminx'))
def test_cached_gates_agree_with_independent_full_vertex_tests_and_keep_cancellation(module):
    from importlib import import_module
    from random import Random
    from cube.crazy_comet import vertices
    from cube.curvy_copter import inverse_point
    from cube.polyhedral import dot
    from cube.planar_twins_state import _local_extent
    c=import_module('solver.'+module)._profile.factory();rng=Random(62)
    for _ in range(8):
        legal=[]
        for axis,normal in enumerate(c.turn_axes):
            bound=c.cut_bounds[axis];expected=[];blocked=False
            for h,(solid,frame) in enumerate(zip(c.solids,c.frames)):
                values=[dot(inverse_point(frame,normal),p) for p in vertices(solid)]
                if min(values)>=bound-1e-8:expected.append(h)
                elif max(values)>bound+1e-8:blocked=True;break
            if blocked or not expected:
                with pytest.raises(ValueError,match='rigid.blocked'):c.selection(axis)
            else:assert c.selection(axis)==tuple(expected)
        choices=list(c.moves());rng.shuffle(choices)
        for m in choices:
            if c.can_apply(m):c.apply_move(m);break
    _local_extent.cache_clear()
    _local_extent(type(c),0,(1.,0.,0.));a=_local_extent(type(c),0,(1.,1e-9,0.))
    points=vertices(c.solids[0]);values=[p[0]+1e-9*p[1] for p in points]
    assert a==(min(values),max(values)) and _local_extent.cache_info().misses==2
    def cancel():raise InterruptedError()
    with pytest.raises(InterruptedError):c.selection(0,cancel)
