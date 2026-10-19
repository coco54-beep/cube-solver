import random

from cube.ghost import GhostCube
from solver.ghost import solve_ghost


def test_first_order_ghost_scrambles_and_solves():
    cube = GhostCube.solved(n=1)
    rng = random.Random(7)
    cube.apply_moves(["@F:" + str(rng.randrange(1, 6)) for _ in range(20)])
    result = solve_ghost(cube)
    replay = cube.clone()
    replay.apply_moves(list(result.moves))
    assert result.success
    assert replay.is_solved()
