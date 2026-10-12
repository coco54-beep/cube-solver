"""五魔方（2/3 阶）求解后处理优化器回归。

验证 ``solver.polyhedral_optimize.optimize_solution`` 减少步数后仍能还原，
并且不会返回比原解更长的序列。
"""

import pytest

from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import scramble, solve_minx


def _solved(cube, solution):
    work = cube.entered()
    for move in solution:
        work.apply_move(move)
    return work.is_solved()


@pytest.mark.parametrize("n,seed", [(3, 1), (2, 1)])
def test_optimizer_shortens_and_still_solves(n, seed):
    cube = PolyhedralPuzzle("megaminx", n)
    scramble(cube, 30 if n == 3 else 12, seed=seed)
    base = solve_minx(cube, optimize=False)
    optimized = solve_minx(cube, optimize=True, optimize_budget=1.5)
    assert _solved(cube, optimized)
    assert len(optimized) <= len(base)
    assert len(optimized) < len(base)


def test_optimizer_never_lengthens():
    cube = PolyhedralPuzzle("megaminx", 3)
    scramble(cube, 25, seed=4)
    base = solve_minx(cube, optimize=False)
    for budget in (0.0, 0.3):
        optimized = solve_minx(cube, optimize=True, optimize_budget=budget)
        assert _solved(cube, optimized)
        assert len(optimized) <= len(base)
