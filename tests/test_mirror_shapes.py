import pytest

from cube.mirror_shape import (MirrorAxisCube, MirrorFisherCube,
                               MirrorWindmillCube, MirrorUnequalWindmillCube,
                               MirrorUnequalFisherCube, MirrorOffsetWindmillCube,
                               MirrorOffsetFisherCube)
from solver.mirror import solve_mirror

CASES = (MirrorWindmillCube, MirrorAxisCube, MirrorFisherCube,
         MirrorUnequalWindmillCube, MirrorUnequalFisherCube,
         MirrorOffsetWindmillCube, MirrorOffsetFisherCube)


@pytest.mark.parametrize("cube_class", CASES)
def test_mirror_shape_starts_solved(cube_class):
    assert cube_class.solved().is_solved()


@pytest.mark.parametrize("cube_class", CASES)
def test_mirror_shape_scrambles_and_solves(cube_class):
    cube = cube_class.solved()
    cube.apply_moves(["R", "U", "F'"])
    assert not cube.is_solved()
    result = solve_mirror(cube)
    assert result.success
    replay = cube.clone()
    replay.apply_moves(result.moves)
    assert replay.is_solved()
