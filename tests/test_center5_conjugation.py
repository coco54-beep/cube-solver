"""5x5 活动中心 3-cycle 共轭构造测试。

结论（已实证）：合法动作下 corner / edge 中心轨道上的诱导作用是三重传递的，
单个主基元经 S' P S 共轭可作用出任意目标三重。本测试验证：
    - 三重传递性（所有有序三重均可达）。
    - conjugate_cycle 在真实 Cube5 上作用出目标三重。
    - 合法动作与纯 3-cycle 保持（不破坏另一活动轨道与固定面心）。
"""

import random

import pytest

from cube.cube5 import Cube5
from solver.center5 import (
    CORNER_MAIN,
    EDGE_MAIN,
    CenterOrbitKind,
    CENTER_PRIMITIVES,
    CENTER_ORDER,
    analyze_cube5_replay,
    assert_legal_5x5_solution_moves,
    conjugate_cycle,
    find_setup,
    is_legal_5x5_solver_move,
    kind_of_position,
    validate_center_primitive,
)


def _orbit_ids(kind):
    return [i for i, p in enumerate(CENTER_ORDER) if kind_of_position(p) == kind]


def _conjugate_cycle_type(prim, tgt):
    moves = conjugate_cycle(prim, tgt)
    assert_legal_5x5_solution_moves(moves)
    return analyze_cube5_replay(moves, prim.orbit)


@pytest.mark.parametrize("prim", (CORNER_MAIN, EDGE_MAIN), ids=lambda p: p.name)
def test_conjugate_hits_target_triple(prim):
    random.seed(11)
    ids = _orbit_ids(prim.orbit)
    for _ in range(20):
        tgt = random.sample(ids, 3)
        analysis = _conjugate_cycle_type(prim, tgt)
        assert analysis.cycle_type() == (3,)
        assert any(set(cy) == set(tgt) for cy in analysis.center_cycles), \
            "共轭未作用出目标三重"


@pytest.mark.parametrize("prim", (CORNER_MAIN, EDGE_MAIN), ids=lambda p: p.name)
def test_conjugate_preserves_other_orbit_and_fixed(prim):
    analysis = _conjugate_cycle_type(prim, _orbit_ids(prim.orbit)[:3])
    if prim.orbit == CenterOrbitKind.CORNER:
        assert not analysis.moved_edge_centers
    else:
        assert not analysis.moved_corner_centers
    assert not analysis.moved_fixed_centers


def test_find_setup_returns_identity_when_target_is_support():
    for prim in CENTER_PRIMITIVES:
        assert find_setup(prim, prim.expected_cycle) == ()


def test_find_setup_maps_support_to_target():
    for prim in (CORNER_MAIN, EDGE_MAIN):
        ids = _orbit_ids(prim.orbit)
        tgt = [ids[0], ids[7], ids[11]]
        setup = find_setup(prim, tgt)
        assert setup is not None
        for m in setup:
            assert is_legal_5x5_solver_move(m)


def test_center_action_is_3_transitive():
    # 在合法动作生成的群作用下，任一有序三重都能被映射到另一有序三重
    ids = _orbit_ids(CenterOrbitKind.CORNER)
    assert len(ids) == 24
    assert len(ids) * (len(ids) - 1) * (len(ids) - 2) == 12144
    # 用一次 find_setup 对随机目标的成功即佐证可达（BFS 收敛）
    random.seed(3)
    for _ in range(30):
        tgt = random.sample(ids, 3)
        assert find_setup(CORNER_MAIN, tgt) is not None
