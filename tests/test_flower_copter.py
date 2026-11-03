"""CAD inventory and regular colour actions; shape tests are in cad_copter_shapes."""
import json
from collections import Counter
import pytest
from cube.flower_copter import FlowerCopterCube,structure
from cube.flower_copter_aligned import scrambled,observed_colors,generators,AlignedFlowerCopter,expand
from cube.polyhedral import Move,key


def test_all_twelve_face_circles_match_the_users_dwg_without_added_diagonal_cuts():
    from pathlib import Path
    import math
    from cube.flower_material import cuts
    data=json.loads((Path(__file__).parent/'data/flower_face_arcs.json').read_text())
    measured=[((r['center'][0]-5)/5,(r['center'][1]-5)/5,r['radius']/5) for r in data['arcs']]
    circles=[]
    for s in cuts():
        radius2=s.radius*s.radius-(s.centre[2]-1)**2
        if radius2>1e-9:circles.append((s.centre[0],s.centre[1],math.sqrt(radius2)))
    assert len(circles)==len(measured)==12
    for circle in circles:
        assert min(max(abs(a-b) for a,b in zip(circle,other)) for other in measured)<2e-8
    c=FlowerCopterCube();faces={}
    from cube.polyhedral import CUBE,dot,cross
    for h,face,p in c.panels:
        faces.setdefault(face,[]).append(p)
        assert all(abs(dot(point,CUBE[face])-1)<1e-8 for point in p)
        if CUBE[face]!=(0.,0.,1.):continue
        for a,b in zip(p,p[1:]+p[:1]):
            if any(abs(a[k]-sign)<1e-8 and abs(b[k]-sign)<1e-8 for k in (0,1) for sign in (-1,1)):continue
            assert any(all(abs((p[0]-x)**2+(p[1]-y)**2-r*r)<1e-7 for p in (a,b)) for x,y,r in circles)
    for face,patches in faces.items():
        area=sum(abs(sum(dot(cross(a,b),CUBE[face])
                         for a,b in zip(p,p[1:]+p[:1])))/2 for p in patches)
        assert abs(area-4)<1e-7


def test_independent_closed_material_and_one_field_per_colour_patch():
    from cube.flower_material import build_masks,panels,residual,cuts
    from renderer.flower_copter_view import surfaces
    c=FlowerCopterCube()
    assert len(c.regions)==161 and len(c.panels)==120
    assert Counter(f for h,f,p in c.panels)=={i:20 for i in range(6)}
    assert Counter(Counter(h for h,f,p in c.panels).values())=={1:72,2:12,3:8}
    assert set(build_masks())==set(c.signatures)
    for home,face,polygon in c.panels:
        mask=c.signatures[home]
        for point in polygon:
            assert all((residual(cut,point) if mask&(1<<i) else -residual(cut,point))<1e-6 for i,cut in enumerate(cuts()))
    assert {slot for row in surfaces() for tri,n,slot in row if slot>=0}==set(range(120))



@pytest.mark.parametrize('axis',range(20))
def test_each_regular_turn_closes_and_reverses_the_entire_material(axis):
    c=FlowerCopterCube();before=c.signature();amount=180. if axis<12 else 120.
    c.apply_move(Move(axis,0,amount));assert not c.is_solved()
    assert sorted(c.aligned_permutation())==list(range(120))
    c.apply_move(Move(axis,0,-amount));assert c.signature()==before


@pytest.mark.parametrize('move',(Move(0,0,90.),Move(12,0,17.),Move(0,1,180.),Move(-1,0,180.)))
def test_unsupported_or_invalid_moves_never_mutate_the_model(move):
    c=FlowerCopterCube();before=c.signature()
    assert not c.can_apply(move)
    with pytest.raises(ValueError):c.apply_move(move)
    assert c.signature()==before


def test_all_compiled_transversals_and_leaf_tools_replay_the_certified_group():
    from solver.flower_copter import _profile
    from solver.polyhedral import apply_word
    data=_profile.data();g=AlignedFlowerCopter().geometry
    assert len(generators())==20 and data['verified_transversals']>0
    for row in data['transversals']:
        for record in row.values():
            assert apply_word(g,tuple(Move(*m) for m in record['word']))==tuple(record['permutation'])
    for row in data['leaf_stages']:
        virtual=tuple(Move(*m) for m in row['word']);effect=apply_word(g,virtual)
        assert sum(i!=j for i,j in enumerate(effect))==3 and len(expand(virtual))>0
        assert FlowerCopterCube().apply_moves(expand(virtual)).aligned_permutation()==effect


@pytest.mark.parametrize('seed',range(4))
@pytest.mark.parametrize('length',(30,100,300))
def test_manual_world_colour_and_measured_pose_reentry_solve_without_history(seed,length):
    from solver.flower_copter import solve
    from app.session import encode,decode
    source=scrambled(seed,length)
    entered=FlowerCopterCube.from_observation(json.loads(json.dumps(source.observation_data())))
    before=entered.signature()
    assert decode(json.loads(json.dumps(encode(entered)))).signature()==before
    word=solve(entered,seconds=15)
    assert entered.signature()==before and entered.clone().apply_moves(word).is_solved()
    flat=FlowerCopterCube(paints=observed_colors(source));before=flat.signature()
    word=solve(flat,seconds=15)
    assert flat.signature()==before and flat.clone().apply_moves(word).is_solved()


def test_cancel_missing_and_out_of_scope_pose_preserve_input_and_failure_category():
    from solver.flower_copter import solve
    from services.failures import classify
    from cube.appearance import IDENTITY_FRAME
    from cube.polyhedral import rotate
    import math
    c=scrambled(41);before=c.signature()
    with pytest.raises(InterruptedError):solve(c,cancel=lambda:True)
    assert c.signature()==before
    with pytest.raises(TimeoutError):solve(c,seconds=0)
    assert c.signature()==before
    c.paint(0,-1);before=c.signature()
    with pytest.raises(ValueError,match='every sticker'):solve(c)
    assert c.signature()==before
    c=FlowerCopterCube();home=c.panels[0][0]
    c.set_piece_frame(home,tuple(rotate(p,(1.,0.,0.),math.radians(17)) for p in IDENTITY_FRAME))
    before=c.signature()
    with pytest.raises(TimeoutError,match='copter.shape_unresolved'):solve(c,seconds=.02)
    assert c.signature()==before and classify('copter.shape_unresolved')=='timeout'


def test_full_rotation_of_a_manually_edited_piece_does_not_lose_colours_or_solvability():
    from solver.flower_copter import solve
    from cube.appearance import IDENTITY_FRAME
    from cube.curvy_copter import multiply
    from cube.polyhedral import rotate
    import math
    c=scrambled(51,100);before=c.signature();home=c.panels[40][0]
    quarter=tuple(rotate(p,(1.,0.,0.),math.pi/2) for p in IDENTITY_FRAME)
    for _ in range(4):c.set_piece_frame(home,multiply(quarter,c.frames[home]))
    assert c.signature()==before
    assert c.clone().apply_moves(solve(c,seconds=15)).is_solved()


def test_routes_regular_angle_controls_and_original_three_piece_formula():
    from candidate_puzzles import catalogue_family,CATALOGUE_FAMILIES
    from demo.expanded_support import make_cube,view_class,entry_screen
    from ui.screens.polyhedral_screen import _entry_for,_view_for
    from ui.screens.flower_copter_screen import FlowerCopterTwistScreen
    from renderer.flower_copter_view import FlowerCopterTwistView
    from demo.expanded_tutorials import lessons,tutorial
    from demo.expanded_curriculum import chapters
    from types import SimpleNamespace
    c=make_cube('lanlan_flower_copter',3)
    assert catalogue_family(c.puzzle_kind)=='edge_family'
    assert sum(c.puzzle_kind in kinds for kinds in CATALOGUE_FAMILIES.values())==1
    assert entry_screen(c.puzzle_kind)==_entry_for(c)=='FlowerCopterInputScreen'
    assert view_class(c.puzzle_kind) is _view_for(c)
    assert _view_for(c,True) is FlowerCopterTwistView
    for axis in range(20):
        expected=180. if axis<12 else 120.
        view=SimpleNamespace(edge_amount=180.,corner_amount=120.)
        assert FlowerCopterTwistView.amount_for_axis(view,axis)==expected
        screen=SimpleNamespace(_axis=axis,layer=SimpleNamespace(),view=SimpleNamespace())
        screen._layer_selected=lambda widget,text:FlowerCopterTwistScreen._layer_selected(screen,widget,text)
        FlowerCopterTwistScreen._set_layers(screen)
        assert screen._angle==expected and screen.view.turn_amount==expected and not screen.layer.disabled
        assert len(screen.layer.values)==(3 if axis<12 else 2)
    formula=[]
    for lesson in lessons(c.puzzle_kind,3):
        for case in lesson['cases']:
            assert case['initial'].clone().apply_moves(case['moves']).is_solved()
            if case.get('original'):formula.append(case)
    assert len(formula)==1 and len(formula[0]['moves'])>0 and len(formula[0]['cycle_pieces'])==3
    assert len(chapters(c.puzzle_kind))==4 and '60°' in tutorial(c.puzzle_kind).intro


def test_active_small_solver_asset_is_included_without_building_a_package():
    from scripts.bundle_assets import ROOT,windows_assets
    selected={p.relative_to(ROOT).as_posix() for p in windows_assets()}
    assert 'solver/data/flower_copter_colour_group.bin' in selected
    assert {'cube/data/flower_regular_material.bin','cube/data/flower_regular_skin.bin'}<=selected


def test_rendering_rest_and_turns_keep_all_fields_and_only_reveal_the_active_internal_cut():
    from renderer.flower_copter_view import FlowerCopterView,surfaces
    from types import SimpleNamespace
    c=scrambled(6,30);view=SimpleNamespace(_move=None,piece_filter=None,
        outer_skin=FlowerCopterView.outer_skin,home_surfaces=FlowerCopterView.home_surfaces,
        skin=FlowerCopterView.skin)
    rest=FlowerCopterView._surfaces(view,c)
    assert {row[3] for row in rest}==set(range(120))
    assert all(row[3] is not None for row in rest)
    full=sum(map(len,surfaces()))
    for axis in range(20):
        view._move=Move(axis,0,180. if axis<12 else 120.)
        shown=FlowerCopterView._surfaces(view,c)
        assert {row[3] for row in shown if row[3] is not None}==set(range(120))
        assert any(row[3] is None for row in shown)
        assert len(shown)<full/3
    view._move=None
    assert FlowerCopterView._surfaces(view,c)==rest
