import random

import pytest

from cube.ghost import GhostCube
from cube.scramble import random_scramble
from cube.shape_cube import AxisCube, FisherCube, WindmillCube
from solver.ghost import solve_ghost
from solver.shape_cube import solve_shape_cube


@pytest.mark.parametrize("cube_class", (AxisCube, WindmillCube, FisherCube))
def test_high_order_shape_cube_solves(cube_class):
    cube = cube_class.solved(n=4)
    cube.apply_moves(random_scramble(4, random.Random(4), cube_class.puzzle_kind))
    result = solve_shape_cube(cube)
    replay = cube.clone()
    replay.apply_moves(list(result.moves))
    assert result.success
    assert replay.is_solved()


def test_high_order_ghost_solves():
    pytest.importorskip("kivy")
    cube = GhostCube.solved(n=4)
    cube.apply_moves(cube.alignment_moves())
    cube.apply_moves(random_scramble(4, random.Random(4), "ghost"))
    result = solve_ghost(cube)
    replay = cube.clone()
    replay.apply_moves(list(result.moves))
    assert result.success
    assert replay.is_solved()
