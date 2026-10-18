import pytest

from cube.mirror_skewb import MirrorSkewbCube
from cube.polyhedral_scramble import scramble
from solver.mirror_skewb import solve_mirror_skewb


def test_solved_mirror_skewb_needs_no_moves():
    assert solve_mirror_skewb(MirrorSkewbCube.solved()) == ()


@pytest.mark.parametrize("seed", range(6))
def test_mirror_skewb_scrambles_solve_completely(seed):
    cube = MirrorSkewbCube.solved()
    scramble(cube, 30, seed)
    word = solve_mirror_skewb(cube)
    replay = cube.clone()
    for move in word:
        replay.apply_move(move)
    assert replay.is_solved()
    assert len(word) <= 16
