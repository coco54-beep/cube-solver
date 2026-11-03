"""Full visible-only entry, real turn permutations and constructive solving."""
import json
import math
from collections import Counter
import pytest
from cube.polyhedral import PolyhedralPuzzle,Move,rotate,key
from cube.dial_beans import KINDS,goal,petals,bean_index,move_origin,INNER
from cube.polyhedral_scramble import scramble
from solver.dial_beans import solve,validate,primitive


@pytest.mark.parametrize('kind,n',KINDS.items())
def test_real_moves_are_bijective_have_the_right_period_and_match_animation(kind,n):
    cube=PolyhedralPuzzle(kind,n);g=cube.geometry;identity=tuple(range(len(cube.colors)))
    for move in cube.moves():
        action=g.permutation(move);assert sorted(action)==list(identity)
        assert g.permutation(Move(move.axis,0,g.spec.turn_order))==identity
        origin=move_origin(kind,move);angle=math.tau*move.amount/g.spec.turn_order
        for i,s in enumerate(g.stickers):
            if s.piece not in g.layers[move.axis][0]:continue
            expected={key(tuple(v+o for v,o in zip(rotate(tuple(a-b for a,b in zip(p,origin)),g.spec.axes[move.axis],angle),origin))) for p in s.polygon}
            assert expected=={key(p) for p in g.stickers[action[i]].polygon}


@pytest.mark.parametrize('kind,n',KINDS.items())
@pytest.mark.parametrize('turns,seed',[(30,20261110),(100,20261110),(30,20261111),(100,20261111)])
def test_serialized_visible_input_solves_without_any_scramble_history(kind,n,turns,seed):
    source=PolyhedralPuzzle(kind,n);scramble(source,turns,seed)
    payload=json.loads(json.dumps({'colours':source.colors}))
    entered=PolyhedralPuzzle(kind,n,payload['colours']);before=tuple(entered.colors)
    assert entered.scramble_history is None and validate(entered)
    word=solve(entered);assert tuple(entered.colors)==before
    replay=entered.entered()
    for move in word:replay.apply_move(move)
    assert replay.is_solved()


@pytest.mark.parametrize('kind,n',KINDS.items())
def test_original_cycle_fixes_every_other_slot_and_repeats_in_three(kind,n):
    cube=PolyhedralPuzzle(kind,n);word,base=primitive(cube)
    from solver.polyhedral import apply_word
    action=apply_word(cube.geometry,word)
    changed={cube.geometry.stickers[i].piece for i,j in enumerate(action) if i!=j}
    assert changed==set(base) and len(changed)==3
    for _ in range(3):
        for move in word:cube.apply_move(move)
    assert cube.is_solved()


@pytest.mark.parametrize('kind',('bean_6','bean_10'))
def test_wing_rotor_and_fixed_transition_beads_are_distinct(kind):
    g=PolyhedralPuzzle(kind,KINDS[kind]).geometry;p=petals(kind)
    wing=g.permutation(Move(2*p,0,g.spec.step(2*p)))
    for side in range(2):
        rotor=g.permutation(Move(3*p+side,0,g.spec.step(3*p+side)))
        for j in range(10):
            slot=bean_index(kind,side,0,j)
            assert (wing[slot]!=slot)==(j<5)
            assert (rotor[slot]!=slot)==(j in INNER)
            opposite=bean_index(kind,1-side,0,j)
            assert rotor[opposite]==opposite
        for j in (5,9):
            slot=bean_index(kind,side,0,j)
            assert wing[slot]==rotor[slot]==slot


@pytest.mark.parametrize('kind',('bean_6','bean_10'))
def test_front_and_back_rotors_are_independent_and_can_be_replayed_from_visible_input(kind):
    cube=PolyhedralPuzzle(kind,KINDS[kind]);p=petals(kind);g=cube.geometry
    assert len(g.spec.axes)==3*p+2
    before=list(cube.colors);half=len(before)//2
    front=Move(3*p,0,g.spec.step(3*p));back=Move(3*p+1,0,g.spec.step(3*p+1))
    cube.apply_move(front)
    assert cube.colors[:half]!=before[:half] and cube.colors[half:]==before[half:]
    after_front=list(cube.colors);cube.apply_move(back)
    assert cube.colors[:half]==after_front[:half] and cube.colors[half:]!=after_front[half:]
    fresh=PolyhedralPuzzle(kind,KINDS[kind],list(cube.colors))
    assert fresh.scramble_history is None
    word=solve(fresh)
    for move in word:fresh.apply_move(move)
    assert fresh.is_solved()


def test_old_shared_rotor_checkpoint_keeps_visible_input_and_drops_obsolete_replay():
    from app.session import migrate_bean_rotors
    cube=PolyhedralPuzzle('bean_6',6);scramble(cube,20,67);visible=cube.entered()
    state={'app':dict(cube=PolyhedralPuzzle('bean_6',6),puzzle_kind='bean_6',polyhedral_solution=('old',)),
           'page':'PolyhedralPlaybackScreen','screens':{'PolyhedralPlaybackScreen':{'_work':visible,'_moves':('old',)}},
           'replay_to':7}
    fixed=migrate_bean_rotors(state)
    assert fixed['app']['cube'].colors==visible.colors and fixed['app']['polyhedral_solution'] is None
    assert fixed['page']=='PolyhedralScreen' and fixed['replay_to'] is None
    assert fixed['screens']['PolyhedralScreen']['_cube'].colors==visible.colors
    assert 'PolyhedralPlaybackScreen' not in fixed['screens']
    assert migrate_bean_rotors(fixed) is fixed


@pytest.mark.parametrize('kind,n',KINDS.items())
def test_partial_bad_count_cancel_and_json_checkpoint(kind,n):
    from app.session import encode,decode
    cube=PolyhedralPuzzle(kind,n);cube.colors[0]=-1
    with pytest.raises(ValueError):validate(cube)
    restored=decode(json.loads(json.dumps(encode(cube))))
    assert restored.colors==cube.colors
    cube=PolyhedralPuzzle(kind,n);cube.colors[0]=cube.colors[-1]
    with pytest.raises(ValueError):validate(cube)
    with pytest.raises(InterruptedError):solve(PolyhedralPuzzle(kind,n),lambda:True)


def test_wrong_time_corner_twist_is_rejected_and_duplicate_numbers_are_rejected():
    cube=PolyhedralPuzzle('time_machine',2);slots=cube.geometry.pieces[0]
    a,b,c=slots;cube.colors[a],cube.colors[b],cube.colors[c]=cube.colors[c],cube.colors[a],cube.colors[b]
    with pytest.raises(ValueError,match='twist'):validate(cube)
    cube=PolyhedralPuzzle('time_machine',2);cube.colors[24]=cube.colors[25]
    with pytest.raises(ValueError):validate(cube)


def test_time_machine_outer_corner_faces_move_with_the_matching_centre_faces():
    cube=PolyhedralPuzzle('time_machine',2);g=cube.geometry
    # Outer surfaces are another exposed part of each corner, not extra
    # independently coloured stickers or numbered ring pieces.
    assert len(cube.colors)==96 and all(len(p)==3 for p in g.pieces[:8])
    for i,s in enumerate(g.stickers[:24]):
        assert s.patches[0]==s.polygon and len(s.patches)>1
        assert any(max(abs(v) for v in p)> .99 for patch in s.patches[1:] for p in patch)
        for move in cube.moves():
            target=g.stickers[g.permutation(move)[i]]
            angle=math.tau*move.amount/g.spec.turn_order
            rotate_piece=s.piece in g.layers[move.axis][0]
            actual={tuple(sorted(key(rotate(p,g.spec.axes[move.axis],angle) if rotate_piece else p)
                                 for p in patch)) for patch in s.patches}
            expected={tuple(sorted(key(p) for p in patch)) for patch in target.patches}
            assert actual==expected


def test_new_models_use_current_families_without_duplicate_entries():
    from candidate_puzzles import CATALOGUE_FAMILIES
    flat=[kind for kinds in CATALOGUE_FAMILIES.values() for kind in kinds]
    assert 'time_machine' in CATALOGUE_FAMILIES['circle_family']
    for kind in ('bean_6','bean_10'):assert kind in CATALOGUE_FAMILIES['round_family']
    assert all(flat.count(kind)==1 for kind in KINDS)


@pytest.mark.parametrize('kind,n',KINDS.items())
def test_production_service_uses_new_solver_and_keeps_original_input(kind,n):
    from services.solve_service import SolveService,CancelToken
    cube=PolyhedralPuzzle(kind,n);scramble(cube,100,20261113);cube=cube.entered()
    before=tuple(cube.colors);answers=[]
    SolveService()._run(cube,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success,answers[0].message
    assert tuple(cube.colors)==before
    replay=cube.entered()
    for move in answers[0].moves:replay.apply_move(move)
    assert replay.is_solved()


@pytest.mark.parametrize('kind,n,axis',[('time_machine',2,0),('bean_6',6,6),('bean_10',10,10)])
def test_core_and_wings_reject_angles_reserved_for_other_controls(kind,n,axis):
    cube=PolyhedralPuzzle(kind,n);before=tuple(cube.colors)
    with pytest.raises(ValueError):cube.apply_move(Move(axis,0,1))
    assert tuple(cube.colors)==before
