"""确定性回归：pair_all_protected 在固定 scramble（同 seed 重放）下必须跨调用、
跨进程（由 fixtures 重放保证）给出完全相同的 moves / paired 计数。

此前曾误报「同 seed 下有 7~10 波动」，实际是各脚本用了不同 scramble 产生器；
本测试锁定真实行为：固定轨迹 → 确定性结果。
"""

import pytest

from cube.cube5 import Cube5
from solver.center5 import solve_centers5
from solver.edge5.state import centers_are_color_solved
from solver.edge5.protected_pairing import pair_all_protected


def _build(scramble):
    c = Cube5.solved()
    c.apply_moves(scramble)
    if not centers_are_color_solved(c):
        cr = solve_centers5(c)
        c.apply_moves(cr.moves)
    return c


# 一段固定的、中心已归面的 scramble 轨迹（翻自 seed=1 时序，稳定可重放）
FIXED_SCRAMBLE = [
    "2R", "L", "U'", "D", "F2", "B", "R'", "2L",
]


def test_pair_all_protected_is_reproducible():
    baseline = None
    for _ in range(3):
        w = _build(FIXED_SCRAMBLE)
        res = pair_all_protected(w)
        key = (res.paired, tuple(res.moves))
        if baseline is None:
            baseline = key
        else:
            assert key == baseline, "pair_all_protected 结果跨调用不确定"
