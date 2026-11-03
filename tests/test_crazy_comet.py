"""Whole-cell clearance, observation reentry, cancellation and public routing."""
from collections import Counter
import json,math
import pytest
from cube.crazy_comet import CometCube,structure,vertices,volume,generators,scrambled,observed_colors,CUT
from cube.polyhedral import EDGE_AXES,Move,dot,rotate,key
from cube.curvy_copter import JUMBLE,multiply
from cube.appearance import IDENTITY_FRAME


def test_positive_closed_cells_cover_the_body_and_each_panel_once():
    masks,solids,panels=structure()
    assert len(masks)==len(set(masks))==75 and len(panels)==132
    assert Counter(f for h,f,p in panels)==Counter({i:11 for i in range(12)})
    assert Counter(sum(h==i for h,f,p in panels) for i in range(len(solids)))=={0:1,1:36,2:24,3:8,4:6}
    assert all(volume(solid)>1e-9 for solid in solids)
    assert sum(volume(solid) for solid in solids)==pytest.approx(4*math.sqrt(2))
    for solid in solids:
        edges=Counter(tuple(sorted((key(a),key(b)))) for poly,f in solid for a,b in zip(poly,poly[1:]+poly[:1]))
        assert set(edges.values())=={2}


@pytest.mark.parametrize('axis',range(12))
def test_regular_involution_and_partial_turn_clearance(axis):
    cube=CometCube();initial=cube.signature();selected=cube.selection(axis)
    for home,solid in enumerate(cube.solids):
        values=[dot(EDGE_AXES[axis],p) for p in vertices(solid)]
        assert (min(values)>=CUT-1e-8)==(home in selected)
    cube.apply_move(Move(axis,0,JUMBLE))
    assert not cube.is_solved()
    blocked=[m for m in cube.moves() if not cube.can_apply(m)]
    assert blocked
    before=cube.signature()
    with pytest.raises(ValueError,match='rigid.blocked'):cube.apply_move(blocked[0])
    assert cube.signature()==before
    cube.apply_move(Move(axis,0,-JUMBLE));assert cube.signature()==initial
    cube.apply_moves((Move(axis,0,180.),)*2);assert cube.signature()==initial


def test_closed_jumble_actions_move_leaves_between_groups_and_replay_involutions():
    from cube.comet_aligned import AlignedComet
    assert len(generators())==36
    for action,word in generators():
        physical=CometCube();physical.apply_moves(word)
        assert physical.aligned_permutation()==action
        abstract=AlignedComet();abstract.apply_move(Move(list(generators()).index((action,word))))
        assert observed_colors(physical)==tuple(abstract.colors)
        physical.apply_moves(word);assert physical.is_solved()


def test_compiled_group_words_are_exact_and_fix_every_previous_base_point():
    from cube.comet_aligned import AlignedComet
    from solver.crazy_comet import prepared
    from solver.polyhedral import apply_word
    base,rows=prepared();g=AlignedComet().geometry;fixed=[];order=1
    for point,row in zip(base,rows):
        order*=len(row)
        for beta,action,word in row:
            assert action[point]==beta and all(action[i]==i for i in fixed)
            assert apply_word(g,word)==action
        fixed.append(point)
    assert order==3128406019636513800272642933016111752061275854602240000000000


@pytest.mark.parametrize('seed',range(5))
@pytest.mark.parametrize('length',(30,100))
def test_closed_shape_colors_reentered_without_history_solve(seed,length):
    from services.solve_service import SolveService,CancelToken
    from services.solution_cache import clear
    clear()
    source=scrambled(seed,length,jumble=False)
    entered=CometCube(paints=(-1,)*132)
    for i,color in enumerate(observed_colors(source)):entered.paint(i,color)
    assert not hasattr(entered,'history')
    before=entered.signature();answers=[]
    SolveService()._run(entered,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success,answers[0].message
    replay=entered.clone();replay.apply_moves(answers[0].moves)
    assert replay.is_solved() and entered.signature()==before


@pytest.mark.parametrize('seed',range(5))
def test_generated_jumbled_observation_reentry_and_full_rotation_do_not_lose_colors(seed):
    from solver.crazy_comet import solve
    source=scrambled(seed,100)
    entered=CometCube.from_observation(json.loads(json.dumps(source.observation_data())))
    turn=tuple(rotate(v,(0.,0.,1.),math.pi/2) for v in IDENTITY_FRAME)
    for home in sorted({p[0] for p in entered.panels}):
        for _ in range(4):entered.set_piece_frame(home,multiply(turn,entered.frames[home]))
    assert entered.signature()==source.signature()
    before=entered.signature();word=solve(entered);replay=entered.clone();replay.apply_moves(word)
    assert replay.is_solved() and entered.signature()==before


def test_pose_edit_and_checkpoint_preserve_unrelated_pieces_and_colors():
    from app.session import encode,decode
    cube=scrambled(37);before=cube.clone();home=0
    turn=tuple(rotate(v,(1.,0.,0.),math.pi/2) for v in IDENTITY_FRAME)
    cube.set_piece_frame(home,multiply(turn,cube.frames[home]))
    assert cube.paints==before.paints
    assert all(a==b for i,(a,b) in enumerate(zip(cube.frames,before.frames)) if i!=home)
    restored=decode(json.loads(json.dumps(encode(cube))))
    assert type(restored) is CometCube and restored.signature()==cube.signature()
    cube.colors=before.colors;assert cube.signature()==before.signature()
    initial=cube.signature()
    with pytest.raises(ValueError):cube.colors=[]
    assert cube.signature()==initial


def test_validation_and_cancellation_preserve_input_and_own_fixed_centres():
    from solver.crazy_comet import solve,solve_colours,validate
    cube=CometCube(paints=(-1,)*132);before=cube.signature()
    with pytest.raises(ValueError,match='every sticker'):solve(cube)
    assert cube.signature()==before
    cube=scrambled(31);before=cube.signature()
    with pytest.raises(InterruptedError):solve(cube,cancel=lambda:True)
    assert cube.signature()==before
    calls=0
    def cancelled():
        nonlocal calls
        calls+=1
        return calls>20
    with pytest.raises(InterruptedError):solve(cube,cancel=cancelled)
    assert calls>20 and cube.signature()==before
    with pytest.raises(TimeoutError):solve_colours(observed_colors(scrambled(7,jumble=False)),seconds=0)
    colors=list(observed_colors(CometCube()));colors[0],colors[1]=colors[1],colors[0]
    with pytest.raises(ValueError):validate(colors)
    cube=CometCube();colors=list(observed_colors(cube));slots=next(p for p in cube.geometry.pieces if len(p)==4)
    colors[slots[0]],colors[slots[1]]=colors[slots[1]],colors[slots[0]]
    with pytest.raises(ValueError,match='mirrored') as exc:validate(colors)
    assert exc.value.locations==[dict(sticker=i) for i in slots]


def test_unresolved_shapes_are_not_reported_as_bad_input(monkeypatch):
    from services.solve_service import SolveService,CancelToken
    from services.solution_cache import clear
    from services.failures import classify
    from app.i18n import CATALOG
    for key in ('copter.shape_unresolved','copter.scramble_timeout','comet.timeout'):
        assert classify(key)=='timeout'
        for lang in ('zh','en','ja'):assert classify(CATALOG[lang][key])=='timeout'
    def unresolved(*args,**kwargs):raise ValueError('copter.shape_unresolved')
    monkeypatch.setattr('solver.curvy_copter.normalize',unresolved)
    clear();cube=scrambled(871);before=cube.signature();answers=[]
    SolveService()._run(cube,answers.append,None,CancelToken())
    assert not answers[0].success and answers[0].failure_category=='timeout'
    assert cube.signature()==before


def test_deleted_research_model_and_old_alias_are_not_public_routes():
    from candidate_puzzles import CATALOGUE_FAMILIES,catalogue_family,BY_KIND
    from demo.expanded_support import make_cube,entry_screen
    from solver.crazy_comet import prepared,ASSET
    for kind in ('planar_rhombic_12','lanlan_crazy_comet'):
        assert catalogue_family(kind) is None
        assert all(kind not in kinds for kinds in CATALOGUE_FAMILIES.values())
        assert kind not in BY_KIND and entry_screen(kind) is None
        with pytest.raises(KeyError):make_cube(kind,3)
    # Offline research files are retained, independently of public app routes.
    assert len(prepared()[0])==132 and ASSET.stat().st_size<26000
