from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble
from solver.polyhedral import solve_polyhedral


def test_dino4_is_four_colour_and_solved():
    cube = PolyhedralPuzzle("dino4", 2)
    assert len(cube.colors) == 24
    assert set(cube.colors) == {0, 1, 2, 3}
    assert cube.is_solved()


def test_dino4_solves_and_replays():
    cube = PolyhedralPuzzle("dino4", 2)
    scramble(cube, 12, seed=3)
    assert not cube.is_solved()
    solution = solve_polyhedral(cube)
    replay = cube.clone()
    for move in solution:
        replay.apply_move(move)
    assert replay.is_solved()
