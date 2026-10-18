import pytest

from cube.square_family import KINDS, SquareFamilyCube
from solver.square_family import solve_square_family


@pytest.mark.parametrize("kind", KINDS)
def test_square_family_scramble_solves_and_replays(kind):
    cube = SquareFamilyCube.solved(kind)
    cube.scramble(30, seed=3)
    word = solve_square_family(cube)
    replay = cube.clone()
    for move in word:
        replay.apply_move(move)
    assert replay.is_solved()
    if kind == "square2":
        assert len(word) <= 320
