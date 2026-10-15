"""Learning filters, case variations, independent setups and timer statistics."""
import random

import pytest

from demo.algorithm_library import groups, prepare_case, solved
from demo.learning import LearningProgress, case_key
from demo.practice import PracticeSession, format_time
from demo.practice_scramble import vary_case, generate_scramble
from demo.formula_notation import compile_algorithm
from cube.conversion import cubies_to_facelets


def first_case(puzzle):
    group = groups(puzzle)[0]
    item = next(i for i in group['cases'] if 'error' not in i)
    return group, item, prepare_case(group, item)


@pytest.mark.parametrize('puzzle', ['2x2', '3x3', 'SQ1', 'Pyraminx'])
def test_random_cases_and_displayed_setups_match_the_model(puzzle):
    group, item, base = first_case(puzzle)
    for seed in range(18):
        case = vary_case(puzzle, base, random.Random(seed))
        session = PracticeSession()
        session.question = {'case': case}
        setup = compile_algorithm(puzzle, session.setup_text())
        entered = solved(puzzle)
        for move in setup:
            entered.apply_move(move)
        if puzzle in ('2x2', '3x3'):
            assert cubies_to_facelets(entered.cubies, entered.n) == cubies_to_facelets(case['initial'].cubies, entered.n)
        elif puzzle == 'SQ1':
            assert (entered.slots, entered.middle) == (case['initial'].slots, case['initial'].middle)
        else:
            assert entered.colors == case['initial'].colors
        for move in case['moves']:
            entered.apply_move(move)
        assert entered.is_solved()


@pytest.mark.parametrize('puzzle', ['2x2', '3x3', 'SQ1'])
def test_independent_setup_when_found_replays_exactly(puzzle):
    _, _, base = first_case(puzzle)
    case = vary_case(puzzle, base, random.Random(9))
    text = generate_scramble(puzzle, case, lambda: False)
    # Search is bounded, so a valid fallback is permitted on slower machines.
    if text is None:
        return
    entered = solved(puzzle)
    for move in compile_algorithm(puzzle, text):
        entered.apply_move(move)
    if puzzle == 'SQ1':
        assert (entered.slots, entered.middle) == (case['initial'].slots, case['initial'].middle)
    else:
        assert cubies_to_facelets(entered.cubies, entered.n) == cubies_to_facelets(case['initial'].cubies, entered.n)


def test_learning_status_and_preferred_formula_round_trip():
    group, item, _ = first_case('3x3')
    progress = LearningProgress()
    assert progress.status('3x3', item) == 'new'
    assert [progress.cycle('3x3', item) for _ in range(3)] == ['learning', 'mastered', 'new']
    progress.prefer('3x3', item, 0)
    restored = LearningProgress(progress.records)
    assert restored.preferred('3x3', item) == 0
    session = PracticeSession(progress=restored)
    session.configure('3x3', [group['id']])
    session.set_filter('preferred')
    assert len(session.pool) == 1
    assert session.next_question()['case']['alternative'] == 0


def test_empty_filter_keeps_the_existing_pool():
    session = PracticeSession()
    session.configure('2x2', ['CLL'])
    pool = session.pool
    with pytest.raises(ValueError):
        session.set_filter('learning')
    assert session.pool is pool and session.filter == 'all'


def test_weak_bag_does_not_repeat_and_mastered_fast_cases_are_filtered():
    session = PracticeSession(rng=random.Random(2))
    session.configure('2x2', ['CLL'])
    _, item = session.pool[-1]
    session.progress.cycle('2x2', item)
    session.progress.cycle('2x2', item)
    session.set_filter('weak')
    assert all(c['name'] != item['name'] for _, c in session.pool)
    keys = [case_key('2x2', session.next_question()['item']) for _ in range(8)]
    assert len(keys) == len(set(keys))


def test_penalties_averages_and_invalid_records():
    records = [{'puzzle': '3x3', 'set': 'PLL', 'seconds': i} for i in range(1, 13)]
    session = PracticeSession(history=records)
    session.configure('3x3', ['PLL'])
    assert session.average(5) == 10
    assert session.average(12) == 6.5
    session.history[-1]['penalty'] = 'DNF'
    assert session.average(5) == 10
    session.history[-2]['penalty'] = 'DNF'
    assert format_time(session.average(5)) == 'DNF'
    session.history[-2]['penalty'] = '+2'
    assert session.average(5) == pytest.approx(32/3)
    session.history.append({'puzzle': '3x3', 'set': 'PLL', 'seconds': float('nan')})
    assert len(session.records()) == 12


def test_penalty_only_changes_the_current_stopped_attempt():
    clock = [0.]
    session = PracticeSession(clock=lambda: clock[0])
    session.configure('2x2', ['CLL'])
    session.next_question()
    assert not session.penalty('+2')
    assert session.start()
    clock[0] = 10.
    session.stop()
    assert session.penalty('+2')
    assert session.stats()['best'] == 12.
    session.next_question()
    assert not session.penalty('DNF')
    assert session.history[-1]['penalty'] == '+2'
