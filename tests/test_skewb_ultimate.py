from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble, scramble_length
from solver.polyhedral import piece_orbits, solve_polyhedral


def test_skewb_ultimate_geometry():
    cube = PolyhedralPuzzle("skewb_ultimate", 3)
    assert len(cube.colors) == 48
    sizes = sorted(len(piece) for piece in cube.geometry.pieces)
    assert sizes == [3] * 8 + [4] * 6


def test_skewb_ultimate_solves_and_replays():
    cube = PolyhedralPuzzle("skewb_ultimate", 3)
    cube.colors = [s.face for s in cube.geometry.stickers]
    scramble(cube, min(20, scramble_length(cube)), seed=7)
    solution = solve_polyhedral(cube)
    replay = cube.clone()
    for move in solution:
        replay.apply_move(move)
    assert replay.is_solved()
    assert len(solution) <= 16


import pytest


@pytest.mark.parametrize("seed", range(4))
def test_skewb_ultimate_short_complete_solution(seed):
    cube = PolyhedralPuzzle("skewb_ultimate", 3)
    cube.colors = [s.face for s in cube.geometry.stickers]
    scramble(cube, scramble_length(cube), seed=seed)
    solution = solve_polyhedral(cube)
    replay = cube.clone()
    for move in solution:
        replay.apply_move(move)
    assert replay.is_solved()
    assert len(solution) <= 16
