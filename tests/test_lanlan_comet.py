"""Scooped physical layout, unbandaged actions and observed-state reentry."""
from collections import Counter
import json,math
import pytest
from cube.lanlan_comet import LanlanCometCube,shell,material_cells,structure,CUT,placements
from cube.lanlan_comet_aligned import generators,scrambled,AlignedComet
from cube.compound_solids import volume,tetrahedral_shell
from cube.crazy_comet import vertices,observed_colors
from cube.polyhedral import Move,EDGE_AXES,dot,key,rotate
from cube.curvy_copter import JUMBLE,multiply
from cube.appearance import IDENTITY_FRAME,ROTATIONS


def test_gold_faces_and_scooped_shell_are_part_of_whole_material():
    cube=LanlanCometCube();solids,panels=structure()
    assert cube.color_count==13 and len(solids)==69 and len(panels)==156
    assert Counter(f for h,f,p in panels)==Counter({**{f:11 for f in range(12)},12:24})
    assert Counter(sum(h==home for h,f,p in panels) for home in range(69))=={0:1,1:12,2:24,3:32}
    assert len(shell())==66 and sum(color==12 for poly,color in shell())==24
    assert sum(volume(s) for parts in material_cells() for s in parts)==pytest.approx(
        sum(volume(s) for s in tetrahedral_shell(shell())),abs=1e-10)
    for solid in solids:
        assert volume(solid)>1e-9
        edges=Counter(tuple(sorted((key(a),key(b)))) for poly,f in solid for a,b in zip(poly,poly[1:]+poly[:1]))
        assert set(edges.values())=={2}
    for home in {h for h,f,p in panels if f==12}:
        assert sorted(f for h,f,p in panels if h==home)[-1]==12
        assert sum(h==home for h,f,p in panels)==3


@pytest.mark.parametrize('axis',range(12))
def test_whole_piece_clearance_partial_reversal_and_double_half_turn(axis):
    cube=LanlanCometCube();initial=cube.signature();selected=cube.selection(axis)
    for h,solid in enumerate(cube.solids):
        values=[dot(EDGE_AXES[axis],p) for p in vertices(solid)]
        assert (min(values)>=CUT-1e-8)==(h in selected)
    cube.apply_move(Move(axis,0,JUMBLE))
    blocked=next(m for m in cube.moves() if not cube.can_apply(m));before=cube.signature()
    with pytest.raises(ValueError,match='rigid.blocked'):cube.apply_move(blocked)
    assert cube.signature()==before
    cube.apply_move(Move(axis,0,-JUMBLE));assert cube.signature()==initial
    cube.apply_moves((Move(axis,0,180.),)*2);assert cube.signature()==initial


def test_one_preparation_exchanges_have_their_own_exact_colour_group():
    from solver.lanlan_comet import prepared,ASSET
    from solver.polyhedral import apply_word
    assert len(generators())==132 and any(len(w)==3 for a,w in generators())
    for action,word in generators():
        physical=LanlanCometCube().apply_moves(word)
        assert physical.aligned_permutation()==action
        physical.apply_moves(word);assert physical.is_solved()
    base,rows=prepared();g=AlignedComet().geometry;fixed=[]
    for point,row in zip(base,rows):
        for beta,action,word in row:
            assert action[point]==beta and all(action[i]==i for i in fixed)
            assert apply_word(g,word)==action
        fixed.append(point)
    assert len(base)==156 and ASSET.stat().st_size<100000


@pytest.mark.parametrize('length',(30,100))
@pytest.mark.parametrize('seed',range(5))
def test_observed_colours_and_jumbled_frames_reentered_without_history(seed,length):
    from solver.lanlan_comet import solve
    source=scrambled(seed,length)
    entered=LanlanCometCube.from_observation(json.loads(json.dumps(source.observation_data())))
    assert not hasattr(entered,'history')
    before=entered.signature();word=solve(entered)
    replay=entered.clone().apply_moves(word)
    assert replay.is_solved() and entered.signature()==before
    flat=scrambled(seed,length,jumble=False)
    entered=LanlanCometCube(paints=observed_colors(flat));word=solve(entered)
    assert entered.clone().apply_moves(word).is_solved()


def test_pose_editor_full_turn_and_json_restore_do_not_change_other_pieces():
    from app.session import encode,decode
    cube=scrambled(37);before=cube.signature();colors=cube.paints
    turn=tuple(rotate(v,(1.,0.,0.),math.pi/2) for v in IDENTITY_FRAME)
    for _ in range(4):cube.set_piece_frame(3,multiply(turn,cube.frames[3]))
    assert cube.signature()==before and cube.paints==colors
    restored=decode(json.loads(json.dumps(encode(cube))))
    assert type(restored) is LanlanCometCube and restored.signature()==before
    original=cube.clone();cube.set_piece_frame(3,multiply(turn,cube.frames[3]))
    assert all(a==b for h,(a,b) in enumerate(zip(cube.frames,original.frames)) if h!=3)
    assert cube.paints==colors


def test_failure_and_cancel_preserve_input_and_report_invalid_slots():
    from solver.lanlan_comet import solve,solve_colours,validate
    cube=LanlanCometCube(paints=(-1,)*156);before=cube.signature()
    with pytest.raises(ValueError,match='every sticker'):solve(cube)
    assert cube.signature()==before
    cube=scrambled(31);before=cube.signature()
    with pytest.raises(InterruptedError):solve(cube,cancel=lambda:True)
    assert cube.signature()==before
    with pytest.raises(TimeoutError):solve_colours(observed_colors(scrambled(1,jumble=False)),seconds=0)
    goal=LanlanCometCube();colors=list(goal.paints)
    one,two=goal.geometry.pieces[0][0],goal.geometry.pieces[1][0]
    colors[one],colors[two]=colors[two],colors[one]
    with pytest.raises(ValueError) as error:validate(colors)
    assert error.value.locations


def test_unique_catalogue_shared_controls_original_course_and_gold_picking():
    from candidate_puzzles import CATALOGUE_FAMILIES,catalogue_family
    from demo.expanded_support import make_cube,entry_screen,view_class
    from demo.expanded_tutorials import lessons
    from renderer.comet_view import physical_surfaces
    kind='lanlan_comet_physical'
    assert catalogue_family(kind)=='edge_family'
    assert sum(kind in group for group in CATALOGUE_FAMILIES.values())==1
    assert type(make_cube(kind,3)) is LanlanCometCube
    assert entry_screen(kind)=='LanlanCometInputScreen' and view_class(kind).__name__=='LanlanCometView'
    assert {s for parts in physical_surfaces() for p,n,s in parts if s>=0}==set(range(156))
    for lesson in lessons(kind,3):
        for case in lesson['cases']:
            replay=case['initial'].clone().apply_moves(case['moves']);assert replay.is_solved()
