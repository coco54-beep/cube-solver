"""Verify visible teaching states/effects, not merely inverse-word closure."""
from types import SimpleNamespace

import pytest

pytest.importorskip("kivy")

from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.cube5 import Cube5
from cube.conversion import cubies_to_facelets
from cube.polyhedral import PolyhedralPuzzle,Move
from demo.cases import CASE_2X2,CASE_3X3,CASE_4X4,CASE_5X5,TEACHING_COLORS,inverse_move_str
from demo.irregular_cases import lessons,token
from demo.cases import localized
from demo.solutions import (build_example,solved_demo_cube,state_signature,
                            verified_solution_lessons,make_scrambled_demo)
from solver.result import SolveResult,SolveStage


# Cover every currently offered irregular model/order through five.
ORDERS={'pyraminx':(2,3,4,5),'mastermorphix':(2,3,4,5),'mirror':(2,3,4,5),
        'skewb':(3,5),'dino':(2,4),'megaminx':(2,3,4,5),'moyu':(3,4,5),
        'fto':(2,3,4),'football':(3,5),'icosahedron':(2,3,4,5),
        'war_drum':(2,3,4,5),'pentahedron':(2,3,4,5)}
SPECIAL=('eight_petals','clover','blossom','square1','void_cube','void_tower',
         'mirror_tower','axis','pandora','windmill','fisher','ivy')
MODES=[2,3,4,5]+[(k,n) for k,ns in ORDERS.items() for n in ns]+[(k,3) for k in SPECIAL]


def steps_for(mode):
    return lessons(*mode) if isinstance(mode,tuple) else {2:CASE_2X2,3:CASE_3X3,4:CASE_4X4,5:CASE_5X5}[mode]


@pytest.mark.parametrize('mode',MODES)
def test_every_case_moves_and_reverses_without_changing_source(mode):
    for step in steps_for(mode):
        for case in step['cases']:
            before=build_example(mode,case)
            start=state_signature(before)
            work=before.clone()
            for move in case['moves']:
                previous=state_signature(work)
                work.apply_move(move)
                assert state_signature(work)!=previous, (mode,case['name'],move)
            assert work.is_solved(), (mode,case['name'])
            for move in reversed(case['moves']):
                from demo.solutions import inverse_demo_move
                work.apply_move(inverse_demo_move(move,work))
            assert state_signature(work)==start
            assert state_signature(before)==start


def test_teaching_palette_and_corner_insertion_states():
    solved=solved_demo_cube(3)
    assert all(set(x for row in grid for x in row)=={TEACHING_COLORS[face]}
               for face,grid in cubies_to_facelets(solved.cubies,3).items())
    for ci,normal in ((0,(1,0,0)),(1,(0,0,1))):
        start=build_example(3,CASE_3X3[1]['cases'][ci])
        corner=next(c for c in start.cubies.values() if c.home==(1,-1,1))
        assert corner.pos==(1,1,1)
        assert corner.stickers[normal]=='W'


def test_cross_alignment_example_really_targets_white_red():
    cube=build_example(3,CASE_3X3[0]['cases'][2])
    piece=next(c for c in cube.cubies.values() if c.home==(1,-1,0))
    assert piece.pos==(0,1,1)
    assert piece.stickers[(0,1,0)]=='W'
    assert piece.stickers[(0,0,1)]=='R'


def test_middle_edge_reversed_example_has_a_reversed_middle_edge():
    cube=build_example(3,CASE_3X3[2]['cases'][2])
    edge=cube.cubies[(1,0,1)]
    assert edge.home==(1,0,1)
    assert edge.stickers[(0,0,1)]=='R'
    assert edge.stickers[(1,0,0)]=='B'


@pytest.mark.parametrize('ci,count',( (0,2),(1,2),(2,0)))
def test_top_cross_line_l_and_dot_have_the_stated_orientation(ci,count):
    cube=build_example(3,CASE_3X3[3]['cases'][ci])
    up=cubies_to_facelets(cube.cubies,3)['U']
    edge_coords=((0,1),(1,2),(2,1),(1,0))
    yellow={i for i,(r,c) in enumerate(edge_coords) if up[r][c]=='Y'}
    assert len(yellow)==count
    if ci==0: assert yellow=={1,3}
    if ci==1: assert any((i+1)%4 in yellow for i in yellow)
    if ci==2: assert up[1][1]=='Y'


def test_two_order_double_sune_is_zero_yellow_corners():
    c=build_example(2,CASE_2X2[1]['cases'][2])
    assert all(x!='Y' for row in cubies_to_facelets(c.cubies,2)['U'] for x in row)


def changed_sticker_pieces(cube):
    base=solved_demo_cube(cube.n)
    return [(p,c) for p,c in cube.cubies.items() if c.stickers!=base.cubies[p].stickers]


def test_four_order_oll_example_only_flips_one_edge_pair():
    c=build_example(4,CASE_4X4[3]['cases'][1])
    changed=changed_sticker_pieces(c)
    assert len(changed)==2
    assert all(len(cu.stickers)==2 and p[1:]==(3,3) for p,cu in changed)


def test_four_order_pll_keeps_corners_and_centers():
    changed=changed_sticker_pieces(build_example(4,CASE_4X4[3]['cases'][0]))
    assert len(changed)==4
    assert all(len(c.stickers)==2 for _,c in changed)


def test_five_order_center_three_cycle_is_three_centers_and_no_fixed_center():
    c=build_example(5,CASE_5X5[0]['cases'][1])
    moved=[x for x in c.cubies.values() if len(x.stickers)==1 and x.pos!=x.home]
    assert len(moved)==3
    assert all(sorted(map(abs,x.pos))==[3,3,6] for x in moved)
    for x in c.cubies.values():
        if len(x.stickers)==1 and sorted(map(abs,x.home))==[0,0,6]: assert x.pos==x.home


def test_five_order_last_two_edges_only_changes_four_wings():
    changed=changed_sticker_pieces(build_example(5,CASE_5X5[1]['cases'][2]))
    assert len(changed)==4
    assert all(len(c.stickers)==2 and sorted(map(abs,p))==[3,6,6] for p,c in changed)


def test_two_order_morphix_does_not_teach_nonexistent_centers():
    first=lessons('mastermorphix',2)[0]
    assert all('中心' not in localized(c['tip'],'zh') for c in first['cases'])


@pytest.mark.parametrize('kind,n',(('football',3),('pentahedron',4)))
def test_mixed_axis_angles_and_turn_labels_are_unambiguous(kind,n):
    cube=PolyhedralPuzzle(kind,n);spec=cube.geometry.spec
    for axis in range(len(spec.axes)):
        forward=Move(axis,0,spec.step(axis))
        s=token(forward,spec)
        assert f'+{360/spec.order(axis):g}°' in s
        reverse=forward.inverse(spec.turn_order)
        if spec.order(axis)>2: assert '-' in token(reverse,spec)
    # Typical-case formula lessons may replace the old three axis examples.
    assert lessons(kind,n)[0]['cases']
    assert all(case['moves'] for case in lessons(kind,n)[0]['cases'])


@pytest.mark.parametrize('move',('R','r','3R2','M',"E'",'S2','x','3U'))
def test_demo_inverse_notation_preserves_layers_and_slices(move):
    assert inverse_move_str(inverse_move_str(move))==move


def test_complete_solution_uses_actual_scramble_state_and_phase_snapshots():
    initial=Cube3.solved(TEACHING_COLORS);initial.apply_moves(['R','U'])
    original=state_signature(initial)
    result=SolveResult(True,["U'","R'"],'',0,2,[SolveStage('a','第一段',["U'"]),SolveStage('b','第二段',["R'"])])
    steps=verified_solution_lessons(initial,result)
    assert state_signature(build_example(3,steps[0]['cases'][0]))==original
    assert state_signature(initial)==original
    phase=steps[-1]['cases'][0]
    expected=initial.clone();expected.apply_move("U'")
    assert state_signature(build_example(3,phase))==state_signature(expected)


def test_complete_demo_can_use_a_verified_uncompacted_phase_path():
    initial=Cube3.solved();initial.apply_move('R2')
    result=SolveResult(True,['R2'],'',0,1,[SolveStage('a','a',['R','R'])])
    steps=verified_solution_lessons(initial,result)
    assert steps[0]['cases'][0]['moves']==('R','R')
    assert len(steps)==2
    result.stages=[SolveStage('a','a',['R'])]
    steps=verified_solution_lessons(initial,result)
    assert steps[0]['cases'][0]['moves']==('R2',)
    assert len(steps)==1


def test_partial_or_failed_solver_result_is_never_presented_as_complete():
    initial=Cube3.solved();initial.apply_moves(['R','U'])
    for result in (SolveResult(False,[], 'failed',0,0),SolveResult(True,["U'"],'',0,1)):
        with pytest.raises(ValueError): verified_solution_lessons(initial,result)


@pytest.mark.parametrize('n',(2,3,4,5))
@pytest.mark.parametrize('move',('x',"y'",'z2'))
def test_whole_cube_solution_moves_have_supported_animation_parameters(n,move):
    from renderer.turn import decompose_move
    from cube.coordinates import coord_values
    from cube.polyhedral import rotate
    import math
    before=solved_demo_cube(n);after=before.clone();after.apply_move(move)
    by_home={c.home:c for c in after.cubies.values()}
    step=decompose_move(move,n)[0]
    assert set(step.layers)==set(coord_values(n))
    axis=tuple(1 if i==step.axis else 0 for i in range(3))
    for c in before.cubies.values():
        predicted=tuple(round(x) for x in rotate(c.pos,axis,math.radians(step.angle)))
        assert predicted==by_home[c.home].pos


@pytest.mark.parametrize('mode',(3,('square1',3),('mirror_tower',3),('football',5),('axis',3)))
def test_complete_demo_starts_with_an_independent_nontrivial_scramble(mode):
    initial=make_scrambled_demo(mode,seed=54)
    assert not initial.is_solved()
    assert state_signature(initial)==state_signature(make_scrambled_demo(mode,seed=54))


@pytest.mark.parametrize('kind',('square1','mirror_tower'))
def test_special_models_dispatch_through_the_shared_solution_service(kind):
    from services.solve_service import SolveService,CancelToken
    cube=solved_demo_cube((kind,3))
    if kind=='square1':
        from cube.square1 import Square1Move
        cube.apply_move(Square1Move(0,3))
    else: cube.apply_move(Move(0,0))
    answers=[]
    SolveService()._run(cube,answers.append,None,CancelToken())
    assert len(answers)==1
    assert verified_solution_lessons(cube,answers[0])


@pytest.mark.parametrize('mode',(4,5))
def test_real_center_and_pairing_phases_have_their_stated_goals(mode):
    from services.solve_service import SolveService,CancelToken
    from collections import defaultdict
    cube=make_scrambled_demo(mode)
    results=[]
    SolveService()._run(cube.clone(),results.append,None,CancelToken())
    steps=verified_solution_lessons(cube,results[0])
    assert len(steps)>=4
    work=cube.clone()
    phases=[s for s in results[0].stages if s.moves]
    maxc=max(max(abs(x) for x in p) for p in work.cubies)
    for phase in phases:
        for m in phase.moves:work.apply_move(m)
        if phase.name in ('centers','center','edge_pairing','reduce_edges','orient'):
            solved=solved_demo_cube(mode)
            assert all(c.stickers==solved.cubies[p].stickers for p,c in work.cubies.items() if len(c.stickers)==1)
        if phase.name in ('edge_pairing','reduce_edges','orient'):
            groups=defaultdict(list)
            for p,c in work.cubies.items():
                if len(c.stickers)==2:
                    slot=tuple((i,1 if x>0 else -1) for i,x in enumerate(p) if abs(x)==maxc)
                    values=(tuple(sorted(c.stickers.values())) if phase.name=='reduce_edges'
                            else tuple(sorted(c.stickers.items())))
                    groups[slot].append(values)
            assert all(len(set(group))==1 for group in groups.values())
    assert work.is_solved()


@pytest.mark.parametrize('mode',MODES)
def test_current_input_action_returns_to_its_own_validating_solver(monkeypatch,mode):
    pytest.importorskip('kivy')
    from ui.screens.demo_menu import DemoMenuScreen,source_screen,Clock
    calls=[]
    name=source_screen(mode)
    source=SimpleNamespace(name=name,_playback=False)
    if name in ('PolyhedralScreen','Square1Screen','MirrorTowerScreen'):
        source.solve=lambda:calls.append(name)
    else:source.start_solve=lambda:calls.append(name)
    manager=SimpleNamespace(current='DemoMenuScreen',get_screen=lambda requested:source if requested==name else None)
    monkeypatch.setattr(Clock,'schedule_once',lambda callback,*_:callback(0))
    DemoMenuScreen.solve_current_input(SimpleNamespace(mode=mode,manager=manager))
    assert manager.current==name
    assert calls==[name]


@pytest.mark.parametrize('mode',[m for m in MODES if isinstance(m,int) or m[0] in ('mastermorphix','mirror','axis','pandora','windmill','fisher')])
def test_cube_animation_angles_layers_and_stickers_match_the_committed_move(mode):
    from renderer.turn import decompose_move
    from cube.polyhedral import rotate
    cube=solved_demo_cube(mode)
    moves={m for s in steps_for(mode) for c in s['cases'] for m in c['moves']}
    for move in moves:
        step=decompose_move(move,cube.n)[0]
        axis=tuple(1 if i==step.axis else 0 for i in range(3))
        after=cube.clone();after.apply_move(move)
        by_home={c.home:c for c in after.cubies.values()}
        for before in cube.cubies.values():
            active=before.pos[step.axis] in step.layers
            def turned(p):
                if not active:return p
                import math
                return tuple(round(x) for x in rotate(p,axis,math.radians(step.angle)))
            assert turned(before.pos)==by_home[before.home].pos,(mode,move)
            assert {turned(normal):color for normal,color in before.stickers.items()}==by_home[before.home].stickers


@pytest.mark.parametrize('mode',[m for m in MODES if isinstance(m,tuple) and m[0] not in ('mastermorphix','mirror','axis','pandora','windmill','fisher','square1','mirror_tower')])
def test_polyhedral_animation_endpoints_match_destination_face_normals(mode):
    from cube.polyhedral import rotate,dot
    import math
    cube=solved_demo_cube(mode);g=cube.geometry
    moves={m for s in steps_for(mode) for c in s['cases'] for m in c['moves']}
    for move in moves:
        moving=set(g.layers[move.axis][move.layer])
        amount=move.amount%g.spec.turn_order
        if amount>g.spec.turn_order/2:amount-=g.spec.turn_order
        angle=amount*2*math.pi/g.spec.turn_order
        for source,destination in enumerate(g.permutation(move)):
            s=g.stickers[source]
            normal=g.spec.normals[s.face]
            if s.piece in moving: normal=rotate(normal,g.spec.axes[move.axis],angle)
            assert dot(normal,g.spec.normals[g.stickers[destination].face])==pytest.approx(1,abs=1e-7)


@pytest.mark.parametrize('kind',('square1','mirror_tower'))
def test_special_surface_animation_reaches_the_next_static_model(kind):
    pytest.importorskip('kivy')
    from renderer.square1_view import Square1View
    from renderer.mirror_tower_view import MirrorTowerView
    view=Square1View if kind=='square1' else MirrorTowerView
    def surface_key(points,color):
        return color,tuple(sorted(tuple(round(v,6) for v in p) for p in points))
    for step in lessons(kind,3):
        for case in step['cases']:
            cube=build_example((kind,3),case)
            for move in case['moves']:
                context=SimpleNamespace(cube=cube,_move=move,_fraction=1.)
                transformed=[]
                for points,normal,color,slot,layer,start,width in view._surfaces(cube):
                    if color<0:continue
                    points,_=view._motion(context,points,normal,slot,layer,start,width)
                    transformed.append(surface_key(points,color))
                cube=cube.clone();cube.apply_move(move)
                expected=[surface_key(p,color) for p,_n,color,*_ in view._surfaces(cube) if color>=0]
                assert sorted(transformed)==sorted(expected),(kind,move)
