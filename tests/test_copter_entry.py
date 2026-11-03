"""Paint/pose transactions and independent observation-to-service round trips."""
import math,json
import pytest
from cube.copter_input import CopterCube,scrambled
from cube.curvy_copter import multiply
from cube.appearance import IDENTITY_FRAME
from cube.polyhedral import Move,rotate


def test_one_pose_edit_preserves_other_pieces_and_every_colour():
    cube=scrambled(73,12);before=cube.clone();home=0
    turn=tuple(rotate(v,(1.,0.,0.),math.pi/2) for v in IDENTITY_FRAME)
    for _ in range(4):
        cube.set_piece_frame(home,multiply(turn,cube.frames[home]))
        assert cube.paints==before.paints
        assert all(a==b for i,(a,b) in enumerate(zip(cube.frames,before.frames)) if i!=home)
    assert cube.signature()==before.signature()
    frames=cube.frames
    cube.paint(0,3);assert cube.frames==frames and cube.paints[1:]==before.paints[1:]
    cube.restore(before);assert cube.signature()==before.signature()


def test_checkpoint_includes_pose_and_paint_and_rejects_bad_data_atomically():
    cube=scrambled(99,14);saved=cube.clone();checkpoint=cube.colors
    cube.apply_move(next(m for m in cube.moves() if cube.can_apply(m)))
    cube.paint(1,-1);cube.colors=checkpoint
    assert cube.signature()==saved.signature()
    from app.session import encode,decode
    restored=decode(json.loads(json.dumps(encode(cube))))
    assert restored.signature()==cube.signature()
    for broken in ([],[0]*72,[(0,((0,0,0),)*3)]*72,[(0,None)]*72):
        before=cube.signature()
        with pytest.raises(ValueError):cube.colors=broken
        assert cube.signature()==before
    home=next(h for h in range(len(cube.frames)) if h not in {p[0] for p in cube.panels})
    with pytest.raises(ValueError):cube.set_piece_frame(home,IDENTITY_FRAME)


def test_full_rotation_of_every_piece_does_not_destroy_solvability():
    from services.solve_service import SolveService,CancelToken
    cube=scrambled(20261027,48);before=cube.clone()
    turn=tuple(rotate(v,(0.,0.,1.),math.pi/2) for v in IDENTITY_FRAME)
    for home in sorted({p[0] for p in cube.panels}):
        for _ in range(4):cube.set_piece_frame(home,multiply(turn,cube.frames[home]))
    assert cube.paints==before.paints
    assert max(abs(a-b) for x,y in zip(cube.frames,before.frames) for u,v in zip(x,y) for a,b in zip(u,v))<1e-12
    answers=[];SolveService()._run(cube,answers.append,None,CancelToken())
    assert answers[0].success
    work=cube.clone();work.apply_moves(answers[0].moves);assert work.is_solved()


@pytest.mark.parametrize('seed',(54,20261027))
@pytest.mark.parametrize('length',(30,100,300))
def test_observed_poses_and_colors_reentered_without_move_history_solve(seed,length):
    from services.solve_service import SolveService,CancelToken
    from tools.audit_copter_entry import measured_euler
    source=scrambled(seed,length)
    # Rebuild rotations from the measured visible pose, not stored frames or
    # a sequence of source turns. The GUI exposes these same X/Y/Z controls.
    entered=CopterCube(paints=(-1,)*72)
    for home,target in enumerate(source.frames):
        if not any(p[0]==home for p in source.panels):continue
        for axis,angle in zip(((1.,0.,0.),(0.,1.,0.),(0.,0.,1.)),measured_euler(target)):
            turn=tuple(rotate(v,axis,math.radians(angle)) for v in IDENTITY_FRAME)
            entered.set_piece_frame(home,multiply(turn,entered.frames[home]))
    for i,color in enumerate(source.paints):entered.paint(i,color)
    assert not hasattr(entered,'history') and not hasattr(entered,'scramble_history')
    assert max(abs(a-b) for x,y in zip(source.frames,entered.frames) for u,v in zip(x,y) for a,b in zip(u,v))<1e-8
    before=entered.signature();answers=[]
    SolveService()._run(entered,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success,answers[0].message if answers else None
    work=entered.clone();work.apply_moves(answers[0].moves)
    assert work.is_solved() and entered.signature()==before


def test_service_missing_bad_shape_and_cancellation_keep_original_input():
    from services.solve_service import SolveService,CancelToken
    broken=CopterCube()
    turn=tuple(rotate(v,(1.,0.,0.),math.pi/2) for v in IDENTITY_FRAME)
    broken.set_piece_frame(0,turn)
    for cube,category in ((CopterCube(paints=(-1,)*72),'incomplete'),(broken,'illegal')):
        before=cube.signature();answers=[]
        SolveService()._run(cube,answers.append,None,CancelToken())
        assert not answers[0].success and answers[0].failure_category==category
        assert cube.signature()==before
    cube=scrambled(12,12);before=cube.signature();answers=[];cancel=CancelToken();cancel.cancel()
    SolveService()._run(cube,answers.append,None,cancel)
    assert not answers[0].success and cube.signature()==before


def test_catalogue_course_and_compiled_data_use_production_model():
    from candidate_puzzles import CATALOGUE_FAMILIES,catalogue_family
    from demo.expanded_support import make_cube,entry_screen,view_class
    from demo.expanded_tutorials import lessons
    from solver.copter_colours import ASSET,prepared
    kind='lanlan_curvy_copter'
    assert catalogue_family(kind)=='edge_family'
    assert sum(kind in kinds for kinds in CATALOGUE_FAMILIES.values())==1
    assert isinstance(make_cube(kind,3),CopterCube) and entry_screen(kind)=='CopterInputScreen'
    assert view_class(kind).__name__=='CopterView'
    assert ASSET.parent.name=='data' and ASSET.stat().st_size<11000
    assert prepared()
    for section in lessons(kind,3):
        for case in section['cases']:
            cube=case['initial'].clone();cube.apply_moves(case['moves']);assert cube.is_solved()
