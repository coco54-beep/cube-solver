"""Formula candidates must agree with native solver notation and replay."""
from pathlib import Path

import pytest

from cube.cube3 import Cube3
from cube.conversion import cubies_to_facelets
from cube.facelet_model import FaceletCube
from cube.polyhedral import PolyhedralPuzzle, Move
from cube.square1 import Square1Cube
from demo.algorithm_library import groups, prepare_case
from demo.formula_notation import FormulaCube, compile_algorithm
from scripts.build_formula_finishes import face_turns
from solver.formula_finishes import FACES, _tables, _decode, shorten, cube3_key


def case(puzzle, group, name=None):
    group = next(g for g in groups(puzzle) if g['id'] == group)
    item = next((i for i in group['cases'] if i['name'] == name), group['cases'][0])
    return prepare_case(group, item)['initial']


@pytest.mark.parametrize('algorithm', [
    "M2 U M2 U2 M2 U M2", "r U r' U'", "l' U2 l F'", "f R f' S E'",
    "y F' U' F U r U r' U2 R' F R F' r U r'",
    "y2 F R' F' R U R U' R' F' r U R' U' r' F R U'",
    "y r' R U R' U' F U F' R U' R' F' r",
])
def test_fixed_grip_conversion_matches_standard_notation_on_scrambled_cube(algorithm):
    actual = Cube3.solved()
    actual.apply_moves(['F', 'U2', "L'", 'R', 'D'])
    reference = FormulaCube(3, actual.clone().cubies)
    reference.apply_moves(compile_algorithm('3x3', algorithm))
    actual.apply_moves(face_turns(algorithm))
    expected = cubies_to_facelets(actual.cubies, 3)
    frames = [reference]
    seen = set()
    for probe in frames:
        faces = cubies_to_facelets(probe.cubies, 3)
        centers = tuple(faces[f][1][1] for f in FACES)
        if centers in seen:
            continue
        seen.add(centers)
        if all(faces[f][1][1] == expected[f][1][1] for f in FACES):
            assert faces == expected
            return
        for rotation in ('x', 'y'):
            child = probe.clone()
            child.apply_move(rotation)
            frames.append(child)
    pytest.fail('Could not align the final grip')


def test_every_packaged_entry_replays_with_native_turn_permutations():
    tables, symmetries = _tables()
    assert set(tables) == {'3x3', 'Megaminx', 'SQ1'}
    assert len(symmetries['3x3']) == 24
    assert len(symmetries['Megaminx']) == 60
    assert Path('solver/data/formula_finishes.bin').stat().st_size < 1024 * 1024
    labels = {f: [[i * 9 + r * 3 + c for c in range(3)] for r in range(3)] for i, f in enumerate(FACES)}
    perms = {}
    for face in FACES:
        for suffix in ('', '2', "'"):
            cube = FaceletCube(labels, 3)
            cube.apply_move(face + suffix)
            perms[face + suffix] = tuple(v for f in FACES for row in cube.facelets[f] for v in row)
    solved = bytes(i // 9 for i in range(54))
    for state, encoded in tables['3x3'].items():
        for move in encoded.split():
            assert move[0] in FACES
            state = bytes(state[i] for i in perms[move])
        assert state == solved
    minx = PolyhedralPuzzle('megaminx', 3)
    for state, encoded in tables['Megaminx'].items():
        cube = PolyhedralPuzzle('megaminx', 3, list(state))
        for move in _decode('Megaminx', encoded):
            cube.apply_move(move)
        assert cube.is_solved()
    for state, encoded in tables['SQ1'].items():
        cube = Square1Cube(tuple(state[:-1]), state[-1])
        cube.validate()
        for move in _decode('SQ1', encoded):
            cube.apply_move(move)
        assert cube.is_solved()


def test_corrected_megaminx_formula_shortens_real_chain_solution():
    from solver.polyhedral import solve_minx
    cube = case('Megaminx', 'MegaminxOLL', '10A+')
    before = solve_minx(cube, optimize=False)
    after = solve_minx(cube, optimize=True, optimize_budget=0)
    assert len(after) <= 12
    assert len(after) < len(before)
    for move in after:
        assert type(move) is Move
        cube.apply_move(move)
    assert cube.is_solved()


@pytest.mark.parametrize('puzzle,group', [('3x3', 'PLL'), ('SQ1', 'SQ1Parity'), ('Megaminx', 'MegaminxPLL')])
def test_catalog_finishes_only_shorten_and_do_not_mutate_the_input(puzzle, group):
    cube = case(puzzle, group)
    if puzzle == '3x3':
        cube = FaceletCube(cubies_to_facelets(cube.cubies, 3), 3)
        from solver.solver3 import _build_cubestring, _parse_solution, sv
        before = _parse_solution(sv.solve(_build_cubestring(cube.facelets), 20, 3))[1]
    elif puzzle == 'SQ1':
        from solver.square1 import solve_square1
        before = solve_square1(cube, optimize_budget=0)
    else:
        from solver.polyhedral import solve_minx
        before = solve_minx(cube, optimize=False)
    snapshot = cube3_key(cube.facelets) if puzzle == '3x3' else tuple(cube.slots) + (cube.middle,) if puzzle == 'SQ1' else tuple(cube.colors)
    after = shorten(puzzle, cube, before, budget=.3)
    assert len(after) <= len(before)
    assert snapshot == (cube3_key(cube.facelets) if puzzle == '3x3' else tuple(cube.slots) + (cube.middle,) if puzzle == 'SQ1' else tuple(cube.colors))
    for move in after:
        cube.apply_move(move)
    assert cube.is_solved()


def test_cancel_and_zero_budget():
    cube = Square1Cube()
    from cube.square1 import Square1Move
    word = (Square1Move(0, 3), Square1Move(0, 9))
    assert shorten('SQ1', cube, word, budget=0) == word
    with pytest.raises(InterruptedError):
        shorten('SQ1', cube, word, cancel=lambda: True)


def test_unverified_index_candidate_is_rejected(monkeypatch):
    import solver.formula_finishes as finishes
    cube = Cube3.solved()
    cube.apply_move('R')
    cube = FaceletCube(cubies_to_facelets(cube.cubies, 3), 3)
    monkeypatch.setattr(finishes, '_tables', lambda: ({'3x3': {cube3_key(cube.facelets): 'U'}}, {}))
    before = ("R'", 'U', "U'")
    after = shorten('3x3', cube, before)
    assert after == before


@pytest.mark.parametrize('frame_index', [7, 29, 51])
def test_minx_finish_works_on_different_last_faces(frame_index):
    from demo.algorithm_library import prepare_algorithm
    _, source = prepare_algorithm('Megaminx', "R U R' U2 R U' R' U2' R' F R F'")
    _, symmetries = _tables()
    _, mapping, _ = symmetries['Megaminx'][frame_index]
    word = tuple(Move(mapping[m.axis], m.layer, m.amount) for m in source)
    cube = PolyhedralPuzzle('megaminx', 3)
    for m in reversed(word):
        cube.apply_move(m.inverse(5))
    before = word + (Move(0, 0, 1), Move(0, 0, 4))
    after = shorten('Megaminx', cube, before, budget=.3)
    assert len(after) < len(before)
    for m in after:
        cube.apply_move(m)
    assert cube.is_solved()


def test_optional_missing_index_keeps_the_state_solver_result(monkeypatch):
    import solver.formula_finishes as finishes
    monkeypatch.setattr(finishes, '_tables', lambda: ({}, {}))
    from cube.square1 import Square1Move
    word = (Square1Move(0, 3), Square1Move(0, 9))
    assert shorten('SQ1', Square1Cube(), word) == word
