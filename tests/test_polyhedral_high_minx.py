"""高阶五魔方（4 阶及以上）降阶求解回归。

验证 ``solve_high_minx`` 的分阶段（保护已解轨道）路径在奇/偶阶都能正确还原。
"""

import pytest

from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import scramble, solve_polyhedral


def _solved(cube, solution):
    work = cube.entered()
    for move in solution:
        work.apply_move(move)
    return work.is_solved()


@pytest.mark.parametrize("n,seed", [(4, 3), (5, 3)])
def test_high_minx_solves(n, seed):
    cube = PolyhedralPuzzle("megaminx", n)
    scramble(cube, 12, seed=seed)
    solution = solve_polyhedral(cube)
    assert _solved(cube, solution)


@pytest.mark.slow
@pytest.mark.parametrize("n,seed", [(7, 3), (9, 3)])
def test_odd_high_minx_solves(n, seed):
    cube = PolyhedralPuzzle("megaminx", n)
    scramble(cube, 12, seed=seed)
    solution = solve_polyhedral(cube)
    assert _solved(cube, solution)


@pytest.mark.parametrize('n', [4,5,13])
@pytest.mark.parametrize('missing', [True,False])
def test_high_minx_invalid_centres_rejected_before_core_solve(n,missing,monkeypatch):
    from solver import polyhedral_reduction
    cube=PolyhedralPuzzle('megaminx',n)
    sticker=next(slots[0] for slots in cube.geometry.pieces if len(slots)==1)
    cube.colors[sticker]=-1 if missing else (cube.colors[sticker]+1)%12

    def must_not_solve_core(*args,**kwargs):
        raise AssertionError('Invalid input reached the expensive core solver')

    monkeypatch.setattr(polyhedral_reduction,'solve_minx',must_not_solve_core)
    with pytest.raises(ValueError,match='enter every sticker' if missing else 'color counts'):
        solve_polyhedral(cube)
