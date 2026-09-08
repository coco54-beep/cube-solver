"""5x5 中心同色等价求解器（solver.center5.solve_centers5_color）回归测试。

覆盖：（1）固定 seed 随机打乱回归，重放后中心按颜色归面且固定面心不动；
（2）已解输入返回空；（3）动作合法；（4）同输入确定；（5）输入不被修改；
（6）同色求解宏数量不多于精确求解（同色等价的收益方向）。
"""

import random

import pytest

from cube.cube5 import Cube5
from solver.center5 import (
    LEGAL_5X5_CENTER_MOVES,
    assert_legal_5x5_solution_moves,
    kind_of_position,
    solve_centers5,
    solve_centers5_color,
)
from solver.center5.orbits import CenterOrbitKind
from solver.edge5.state import centers_are_color_solved

_ALL_LEGAL = tuple(LEGAL_5X5_CENTER_MOVES)


def make_legal_scramble(seed: int, length: int = 25) -> list:
    rng = random.Random(seed)
    return [rng.choice(_ALL_LEGAL) for _ in range(length)]


def _fixed_centers_at_home(cube) -> bool:
    for cubie in cube.cubies.values():
        if len(cubie.stickers) == 1:
            if kind_of_position(cubie.home) == CenterOrbitKind.FIXED and cubie.pos != cubie.home:
                return False
    return True


@pytest.mark.parametrize("seed", range(12))
def test_seed_regression(seed):
    cube = Cube5.solved()
    cube.apply_moves(make_legal_scramble(seed=seed, length=25))

    res = solve_centers5_color(cube)
    assert res.success, "seed %d 失败: %s" % (seed, res.message)

    replay = cube.clone()
    replay.apply_moves(list(res.moves))
    assert centers_are_color_solved(replay), "重放后中心未按颜色归面"
    assert _fixed_centers_at_home(replay), "固定面心被扰动"


def test_solved_input_returns_empty():
    res = solve_centers5_color(Cube5.solved())
    assert res.success
    assert res.moves == ()
    assert res.corner_cycle_count == 0
    assert res.edge_cycle_count == 0


def test_all_moves_legal():
    cube = Cube5.solved()
    cube.apply_moves(make_legal_scramble(seed=5, length=30))
    res = solve_centers5_color(cube)
    assert res.success
    assert_legal_5x5_solution_moves(list(res.moves))


def test_same_input_deterministic():
    cube = Cube5.solved()
    cube.apply_moves(make_legal_scramble(seed=9, length=25))
    a = solve_centers5_color(cube)
    b = solve_centers5_color(cube)
    assert a.moves == b.moves
    assert a.corner_cycle_count == b.corner_cycle_count
    assert a.edge_cycle_count == b.edge_cycle_count


def test_input_not_mutated():
    cube = Cube5.solved()
    cube.apply_moves(make_legal_scramble(seed=13, length=25))
    frozen = cube.clone()
    solve_centers5_color(cube)
    for pos, cubie in cube.cubies.items():
        assert cubie.pos == frozen.cubies[pos].pos
        assert cubie.home == frozen.cubies[pos].home


@pytest.mark.parametrize("seed", range(8))
def test_macro_count_not_worse_than_exact(seed):
    cube = Cube5.solved()
    cube.apply_moves(make_legal_scramble(seed=seed, length=25))
    color = solve_centers5_color(cube)
    exact = solve_centers5(cube)
    color_macros = color.corner_cycle_count + color.edge_cycle_count
    exact_macros = exact.corner_cycle_count + exact.edge_cycle_count
    assert color_macros <= exact_macros
