"""5x5 中心奇偶前缀表（PARITY_PREFIX）测试。

奇偶规律（实测并冻结）：corner 轨道奇偶按外层/宽层**四分一转次数**翻转（180° 为偶，
不翻转）；edge 轨道奇偶只被**外层四分一转**翻转（宽转只翻 corner）。
前缀应在执行后把两轨道奇偶都归 0。四种奇偶组合逐一覆盖。
"""

import pytest

from cube.cube5 import Cube5
from solver.center5.orbits import CenterOrbitKind
from solver.center5.permutation import (
    build_pos_to_home_permutation,
    permutation_parity,
)
from solver.center5.solver import (
    PARITY_PREFIX,
    choose_center_parity_prefix,
)


def _parities(cube):
    cp = permutation_parity(build_pos_to_home_permutation(cube, CenterOrbitKind.CORNER))
    ep = permutation_parity(build_pos_to_home_permutation(cube, CenterOrbitKind.EDGE))
    return cp, ep


def _cube_after(moves):
    c = Cube5.solved()
    c.apply_moves(list(moves))
    return c


# 各组合的构造序列（测得实际奇偶与此一致）。
_COMBOS = {
    (0, 0): ["R2", "U2", "F2", "B2"],
    (1, 0): ["2R"],
    (1, 1): ["R"],
    (0, 1): ["R", "2R"],
}


@pytest.mark.parametrize("combo", sorted(_COMBOS), ids=str)
def test_prefix_covers_all_combos(combo):
    assert combo in PARITY_PREFIX


def test_prefix_table_consultation():
    assert choose_center_parity_prefix(0, 0) == ()
    assert choose_center_parity_prefix(1, 0) == ("2R",)
    assert choose_center_parity_prefix(1, 1) == ("R",)
    assert choose_center_parity_prefix(0, 1) == ("2R", "R")


@pytest.mark.parametrize("combo", sorted(_COMBOS), ids=str)
def test_prefix_produces_even_parities(combo):
    cube = _cube_after(_COMBOS[combo])
    cp, ep = _parities(cube)
    assert (cp, ep) == combo, "构造序列未得到目标奇偶组合"
    prefix = choose_center_parity_prefix(cp, ep)
    cube.apply_moves(list(prefix))
    ncp, nep = _parities(cube)
    assert ncp == 0 and nep == 0, "前缀后奇偶应均为 0，实际 (%d, %d)" % (ncp, nep)
