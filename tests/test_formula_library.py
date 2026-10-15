"""Standard notation, case prerequisites and timed training behaviour."""
import random

import pytest

from demo.algorithm_library import groups, prepare_case, verify_case_scope
from demo.formula_notation import FormulaCube, compile_algorithm, expand
from demo.practice import PracticeSession, format_time
from demo.solutions import state_signature


@pytest.mark.parametrize('symbol,equivalent', [
    ('M', "L' R x'"), ('E', "D' U y'"), ('S', "F' B z"),
    ('r', 'x L'), ('u', 'y D'), ('f', 'z B'),
])
def test_standard_slices_and_wide_moves_match_independent_face_rotation_identity(symbol, equivalent):
    direct, reference = FormulaCube(3), FormulaCube(3)
    direct.apply_move(symbol)
    reference.apply_moves(equivalent.split())
    assert state_signature(direct) == state_signature(reference)


def test_published_second_slice_is_not_a_two_layer_wide_turn():
    assert compile_algorithm('4x4', '2R2') == ('r2', 'R2')
    assert compile_algorithm('4x4', 'Rw2') == ('r2',)


def test_group_repetition_and_commutator_notation():
    assert expand("(R U R' U')2") == ['R', 'U', "R'", "U'", 'R', 'U', "R'", "U'"]
    assert expand('[R,U]') == ['R', 'U', "R'", "U'"]


@pytest.mark.parametrize('move,axis,layers,angle', [('r', 0, (1, 0), -90),
                                                 ('M', 0, (0,), 90),
                                                 ('E', 1, (0,), 90),
                                                 ('S', 2, (0,), -90)])
def test_animation_uses_the_same_standard_slice_direction_and_width(move, axis, layers, angle):
    from demo.formula_notation import animation_steps
    step = animation_steps(move, FormulaCube(3))[0]
    assert (step.axis, step.layers, step.angle) == (axis, layers, angle)


def test_pyraminx_uppercase_turn_includes_the_tip_and_body():
    from demo.formula_notation import polyhedral_moves
    upper, = polyhedral_moves('U', 'pyraminx')
    tip, = polyhedral_moves('u', 'pyraminx')
    assert upper.axis == tip.axis
    assert upper.layers == (0, 1)
    assert tip.layers == (0,)


def test_sarah_advanced_primary_choices_preserve_a_completed_first_face():
    group = groups('Skewb')[0]
    for item in group['cases']:
        case = prepare_case(group, item)
        verify_case_scope('Skewb', group['id'], case['initial'])


def test_oll_examples_really_start_with_the_first_two_layers_solved():
    group = next(g for g in groups('3x3') if g['id'] == 'OLL')
    assert len(group['cases']) == 57
    for item in group['cases']:
        verify_case_scope('3x3', 'OLL', prepare_case(group, item)['initial'])


def test_timer_uses_monotonic_time_and_records_only_once():
    now = [100.]
    session = PracticeSession(rng=random.Random(4), clock=lambda: now[0])
    session.configure('2x2', ['OrtegaOLL'])
    session.next_question()
    assert session.start()
    now[0] += 12.34
    assert session.stop()['seconds'] == pytest.approx(12.34)
    assert session.stop() is None
    assert session.stats()['count'] == 1
    assert not session.start()


def test_answer_peeking_does_not_count_as_a_completed_attempt():
    session = PracticeSession(clock=lambda: 10.)
    session.configure('3x3', ['PLL'])
    session.next_question()
    session.start()
    session.reveal()
    assert session.stop() is None
    assert session.stats()['count'] == 0
    assert not session.start()


@pytest.mark.parametrize('puzzle,sets', [('2x2', ['CLL', 'EG1']), ('3x3', ['OLL', 'PLL']),
                                       ('SQ1', ['SQ1CO', 'SQ1CP']), ('Pyraminx', ['L3E', 'L4E'])])
def test_training_supports_multiple_selected_sets_and_no_repeat_within_a_bag(puzzle, sets):
    session = PracticeSession(rng=random.Random(8))
    session.configure(puzzle, sets)
    selected = set()
    for _ in range(min(len(session.pool), 12)):
        question = session.next_question()
        identity = (question['item']['set_id'], question['item']['name'])
        assert identity not in selected
        selected.add(identity)
        assert question['group']['id'] in sets


def test_stats_filter_other_puzzles_and_other_formula_sets():
    history = [{'puzzle': '3x3', 'set': 'PLL', 'seconds': 5.},
               {'puzzle': '3x3', 'set': 'OLL', 'seconds': 20.},
               {'puzzle': '2x2', 'set': 'CLL', 'seconds': 3.}]
    session = PracticeSession(history=history)
    session.configure('3x3', ['PLL'])
    assert session.stats() == {'count': 1, 'best': 5., 'mean': 5.}
    assert format_time(65.789) == '1:05.78'


@pytest.mark.parametrize('puzzle,set_id,name', [
    ('3x3', '1LLL', '1LLL 2 28'),
    ('3x3', '1LLL', '1LLL 5 42'),
    ('Megaminx', 'MegaminxOLL', '10A+'),
])
def test_curated_algorithms_preserve_the_stage_and_replay_every_alternative(puzzle, set_id, name):
    from demo.algorithm_library import prepare_algorithm
    group = next(g for g in groups(puzzle) if g['id'] == set_id)
    item = next(c for c in group['cases'] if c['name'] == name)
    assert 'error' not in item
    for algorithm in item['algorithms']:
        cube, moves = prepare_algorithm(puzzle, algorithm)
        verify_case_scope(puzzle, set_id, cube)
        for move in moves:
            cube.apply_move(move)
        assert cube.is_solved()


@pytest.mark.parametrize('name,oll_number', [('1LLL 2 28', 2), ('1LLL 5 42', 5)])
def test_curated_1lll_has_the_expected_oll_shape(name, oll_number):
    from cube.conversion import cubies_to_facelets
    from demo.algorithm_library import prepare_algorithm

    def mask(cube):
        faces = cubies_to_facelets(cube.cubies, 3)
        top = faces['U'][1][1]
        return tuple(v == top for face in ('U', 'F', 'R', 'B', 'L')
                     for row in (faces[face] if face == 'U' else faces[face][:1])
                     for v in row)

    oll = next(g for g in groups('3x3') if g['id'] == 'OLL')
    target = next(c for c in oll['cases'] if c['name'] == f'OLL {oll_number}')
    reference = prepare_case(oll, target)['initial']
    shapes = set()
    for _ in range(4):
        shapes.add(mask(reference))
        reference.apply_move('y')
    group = next(g for g in groups('3x3') if g['id'] == '1LLL')
    item = next(c for c in group['cases'] if c['name'] == name)
    for algorithm in item['algorithms']:
        cube, _ = prepare_algorithm('3x3', algorithm)
        assert mask(cube) in shapes


def test_curated_catalog_has_no_pending_cases():
    from demo.algorithm_library import catalog
    cases = [c for g in catalog()['sets'] for c in g['cases']]
    assert len(cases) == 6060
    assert all('error' not in c for c in cases)
