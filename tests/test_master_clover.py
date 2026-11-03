"""Regular double-layer kinematics, bonded input and history-free solving."""
from collections import Counter
import json,math
import pytest
from cube.master_clover import MasterCloverCube,centre
from cube.master_clover_aligned import scrambled,observed_colors,generators
from cube.polyhedral import Move,CUBE,cross,dot,rotate
from candidate_puzzles import BY_KIND


def test_regular_shell_has_twenty_fields_and_bonded_corner_centre_pairs():
    c=MasterCloverCube();g=c.geometry
    assert len(c.panels)==120 and len(c.frames)==68
    assert Counter(f for h,f,p in c.panels)=={i:20 for i in range(6)}
    assert Counter(map(len,g.pieces))=={6:8,2:12,1:48}
    for h in range(8):
        assert Counter(c.panels[s][1] for s in g.pieces[h])=={f:2 for f in set(c.panels[s][1] for s in g.pieces[h])}
    for face in range(6):
        area=sum(abs(sum(dot(cross(a,b),CUBE[f]) for a,b in zip(p,p[1:]+p[:1])))/2
                 for h,f,p in c.panels if f==face)
        assert math.isclose(area,4.,abs_tol=1e-8)


@pytest.mark.parametrize('axis',range(12))
@pytest.mark.parametrize('layer',(0,1))
def test_deep_and_shallow_half_turns_have_distinct_whole_piece_actions(axis,layer):
    root=MasterCloverCube();before=root.signature();selected=root.selection(axis,layer)
    assert len(selected)==(11 if layer==0 else 5)
    assert sum(h<8 for h in selected)==(2 if layer==0 else 0)
    c=root.clone().apply_move(Move(axis,layer,180.));action=c.aligned_permutation()
    assert sum(i!=j for i,j in enumerate(action))==(22 if layer==0 else 6)
    assert c.clone().apply_move(Move(axis,layer,-180.)).signature()==before
    assert root.signature()==before


@pytest.mark.parametrize('seed',range(4))
@pytest.mark.parametrize('length',(30,100,300))
def test_fresh_face_by_face_colour_entry_solves_without_history(seed,length):
    from solver.master_clover import solve
    source=scrambled(seed,length);measured=observed_colors(source)
    entered=MasterCloverCube(paints=(-1,)*120)
    for face in range(6):
        for i,(h,f,p) in enumerate(entered.panels):
            if face==f:entered.paint(i,measured[i])
    before=entered.signature();word=solve(entered,seconds=10)
    assert entered.signature()==before and entered.clone().apply_moves(word).is_solved()
    assert not hasattr(entered,'history') and not hasattr(entered,'scramble_history')


def test_service_session_cancel_partial_rotation_and_failure_preserve_input():
    from app.session import encode,decode
    from services.solve_service import SolveService,CancelToken
    from solver.master_clover import solve
    from services.failures import classify
    c=scrambled(23,100);before=c.signature();copy=decode(json.loads(json.dumps(encode(c))))
    assert type(copy) is MasterCloverCube and copy.signature()==before
    with pytest.raises(InterruptedError):solve(c,cancel=lambda:True)
    with pytest.raises(TimeoutError):solve(c,seconds=0)
    with pytest.raises(ValueError,match='master_clover.regular_only'):c.apply_move(Move(0,1,70.528779))
    assert classify('master_clover.regular_only')=='timeout' and c.signature()==before
    results=[];SolveService()._run(c,results.append,None,CancelToken())
    assert results[0].success and c.clone().apply_moves(results[0].moves).is_solved() and c.signature()==before
    c.paint(0,-1);before=c.signature();results=[];SolveService()._run(c,results.append,None,CancelToken())
    assert results[0].failure_category=='incomplete' and c.signature()==before


@pytest.mark.skipif('lanlan_master_clover' not in BY_KIND, reason='Master Clover removed from catalogue')
def test_bonded_corner_observation_and_isolated_three_wing_lesson():
    from solver.master_clover import validate
    from demo.expanded_tutorials import lessons
    c=MasterCloverCube();colours=list(observed_colors(c));ids=c.geometry.pieces[0]
    first=ids[0];same=next(s for s in ids[1:] if c.panels[s][1]==c.panels[first][1])
    other=next(i for i,x in enumerate(colours) if x!=colours[first] and i not in ids)
    colours[first],colours[other]=colours[other],colours[first]
    with pytest.raises(ValueError):validate(colours)
    formulas=[]
    for lesson in lessons(c.puzzle_kind,3):
        for case in lesson['cases']:
            assert case['initial'].clone().apply_moves(case['moves']).is_solved()
            if case.get('original'):formulas.append(case)
    assert len(formulas)==1 and len(formulas[0]['cycle_pieces'])==3


@pytest.mark.skipif('lanlan_master_clover' not in BY_KIND, reason='Master Clover removed from catalogue')
def test_routes_and_current_asset_selection_are_native_not_pending_aliases():
    from demo.expanded_support import make_cube,entry_screen,view_class
    from candidate_puzzles import PENDING_KINDS,catalogue_family
    from ui.screens.polyhedral_screen import _entry_for,_view_for
    from scripts.bundle_assets import windows_assets,ROOT
    c=make_cube('lanlan_master_clover',3)
    assert type(c) is MasterCloverCube and c.puzzle_kind not in PENDING_KINDS
    assert catalogue_family(c.puzzle_kind)=='edge_family'
    assert entry_screen(c.puzzle_kind)==_entry_for(c)=='MasterCloverInputScreen'
    assert view_class(c.puzzle_kind) is _view_for(c)
    selected={p.relative_to(ROOT).as_posix() for p in windows_assets()}
    assert {'cube/data/master_clover_shell.bin','solver/data/master_clover_colour_group.bin'}<=selected
