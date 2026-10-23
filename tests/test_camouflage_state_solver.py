"""Visible six-view entry followed by history-free solve and physical replay."""
import pytest
from cube.cuboid import CuboidCube
from cube.polyhedral_scramble import scramble
from tests.test_camouflage_six_view_entry import enter_visible_panels,visible_state
from solver.cuboid import solve_cuboid


@pytest.mark.parametrize('seed,length',[(20261023,24)]+[(i,40) for i in range(6)])
def test_reentered_camouflage_scrambles_solve(seed,length):
    source=CuboidCube.solved('camouflage_3');scramble(source,length,seed)
    draft=enter_visible_panels(source);result=draft.match(seconds=10)
    assert result.status=='ok'
    cube=result.cube
    assert cube.history is None
    assert visible_state(cube,draft.model)==visible_state(source,draft.model)
    before=visible_state(cube,draft.model);word=solve_cuboid(cube)
    assert cube.history is None and visible_state(cube,draft.model)==before
    for move in word:cube.apply_move(move)
    assert cube.is_solved()
