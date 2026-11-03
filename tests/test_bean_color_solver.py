"""Free ring-colour goals, indistinguishable beads and measured short paths."""
import itertools
import json
import random

import pytest

from cube.dial_beans import KINDS,LOOP,petals,goal
from cube.polyhedral import PolyhedralPuzzle,Move
from cube.polyhedral_scramble import scramble
from solver.dial_beans import solve,validate,primitive


@pytest.mark.parametrize('kind,n',[('bean_6',6),('bean_10',10)])
def test_monochrome_rings_are_complete_in_any_colour_order_without_search(kind,n,monkeypatch):
    import solver.beans
    def unexpected(*args):raise AssertionError('A complete colour arrangement must not be searched')
    monkeypatch.setattr(solver.beans,'solve_beans',unexpected)
    choices=(itertools.permutations(range(n)) if n==6 else
             (random.Random(seed).sample(range(n),n) for seed in range(64)))
    for order in choices:
        colors=[c for c in order for _ in range(LOOP)];cube=PolyhedralPuzzle(kind,n,colors)
        assert validate(cube) and cube.is_solved() and solve(cube)==()
        assert cube.colors==colors


@pytest.mark.parametrize('kind,n',[('bean_6',6),('bean_10',10)])
def test_incomplete_or_wrong_inventory_is_not_a_complete_monochrome_puzzle(kind,n):
    for values in ([-1]*(n*LOOP),[0]*(n*LOOP),[n]*(n*LOOP)):
        cube=PolyhedralPuzzle(kind,n,values);assert not cube.is_solved()
        with pytest.raises(ValueError):validate(cube)


@pytest.mark.parametrize('kind,n',[('bean_6',6),('bean_10',10)])
@pytest.mark.parametrize('control',('wing','front','back'))
def test_one_turn_from_a_noncanonical_complete_arrangement_takes_one_turn_to_solve(kind,n,control):
    cube=PolyhedralPuzzle(kind,n,[c for c in reversed(range(n)) for _ in range(LOOP)])
    p=petals(kind);axis={'wing':2*p,'front':3*p,'back':3*p+1}[control]
    cube.apply_move(Move(axis,0,cube.geometry.spec.step(axis)))
    cube=cube.entered();before=list(cube.colors);word=solve(cube)
    assert len(word)==1 and cube.colors==before and cube.scramble_history is None
    for move in word:cube.apply_move(move)
    assert cube.is_solved()


@pytest.mark.parametrize('kind,n',[('bean_6',6),('bean_10',10)])
def test_short_tool_is_a_pure_three_cycle_and_a_two_colour_swap_needs_no_parity_error(kind,n):
    from solver.polyhedral import apply_word
    cube=PolyhedralPuzzle(kind,n);word,_=primitive(cube)
    assert len(word)==8
    assert sum(i!=j for i,j in enumerate(apply_word(cube.geometry,word)))==3
    cube.colors[0],cube.colors[LOOP]=cube.colors[LOOP],cube.colors[0]
    word=solve(cube)
    for move in word:cube.apply_move(move)
    assert cube.is_solved()


@pytest.mark.parametrize('kind,n,limit',[('bean_6',6,400),('bean_10',10,650)])
@pytest.mark.parametrize('turns',(30,100))
@pytest.mark.parametrize('seed',(20261026,20261027,20261028,20261029))
def test_deep_visible_input_has_a_shorter_verified_colour_solution(kind,n,limit,turns,seed):
    source=PolyhedralPuzzle(kind,n);scramble(source,turns,seed)
    values=json.loads(json.dumps(source.colors));cube=PolyhedralPuzzle(kind,n,values)
    assert cube.scramble_history is None
    word=solve(cube);assert len(word)<=limit and cube.colors==values
    for move in word:cube.apply_move(move)
    assert cube.is_solved()


@pytest.mark.parametrize('kind,n',[('bean_6',6),('bean_10',10)])
@pytest.mark.parametrize('seed',(81,82))
def test_arbitrary_manual_colour_arrangements_solve_without_generator_history(kind,n,seed):
    values=list(goal(kind));random.Random(seed).shuffle(values)
    cube=PolyhedralPuzzle(kind,n,values);before=list(cube.colors);word=solve(cube)
    assert cube.colors==before
    for move in word:cube.apply_move(move)
    assert cube.is_solved()


def test_cancel_during_optional_grouping_preserves_input():
    cube=PolyhedralPuzzle('bean_10',10);scramble(cube,100,20261026);before=list(cube.colors);calls=[]
    def cancel():calls.append(1);return len(calls)>4
    with pytest.raises(InterruptedError):solve(cube,cancel)
    assert cube.colors==before


def test_numbered_time_machine_keeps_its_exact_goal():
    cube=PolyhedralPuzzle('time_machine',2)
    cube.colors[24:36],cube.colors[36:48]=cube.colors[36:48],cube.colors[24:36]
    assert not cube.is_solved()


def test_free_ring_target_keeps_the_maximum_number_of_existing_colours():
    from solver.beans import nearest_target
    values=list(goal('bean_6'));random.Random(52).shuffle(values)
    target=nearest_target(values,6)
    actual=sum(a==b for a,b in zip(values,target))
    expected=max(sum(values[r*LOOP:(r+1)*LOOP].count(c) for r,c in enumerate(order))
                 for order in itertools.permutations(range(6)))
    assert actual==expected


@pytest.mark.parametrize('kind,n',[('bean_6',6),('bean_10',10)])
def test_production_service_accepts_an_already_complete_noncanonical_arrangement(kind,n):
    from services.solve_service import SolveService,CancelToken
    values=[c for c in reversed(range(n)) for _ in range(LOOP)]
    cube=PolyhedralPuzzle(kind,n,values);results=[]
    SolveService()._run(cube,results.append,None,CancelToken())
    assert len(results)==1 and results[0].success and not results[0].moves
    assert cube.colors==values


def test_old_fixed_colour_replay_is_recomputed_without_losing_its_visible_input():
    from app.session import migrate_bean_rotors
    cube=PolyhedralPuzzle('bean_6',6);scramble(cube,30,20261026)
    state={'bean_rotors_version':2,'app':dict(cube=cube,puzzle_kind='bean_6',polyhedral_solution=('long-old-answer',)),
           'page':'PolyhedralPlaybackScreen','screens':{'PolyhedralPlaybackScreen':{'_work':cube}},'replay_to':0}
    fixed=migrate_bean_rotors(state)
    assert fixed['bean_color_goal_version']==2 and fixed['page']=='PolyhedralScreen'
    assert fixed['app']['cube'].colors==cube.colors and fixed['app']['polyhedral_solution'] is None
    assert migrate_bean_rotors(fixed) is fixed
