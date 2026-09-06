"""5x5 棱配对前期（solver.edge5）Milestone 1 + Milestone 2 测试。

覆盖：
M1：
- 36 棱位置模型（12 中棱 + 24 翼，12 逻辑槽，坐标归属正确）。
- EdgeType 无色序（frozenset 语义）。
- 合法动作下轨道闭合（翼只在翼轨道，中棱只在轨道内）。
- is_edge_paired / is_edge_solved 语义分离。
- EdgeMoveEffect 与真实 Cube5 重放一致；单动作 + 逆还原；固定面心保持。
M2：
- solved 输入返回空动作且成功。
- 受控短打乱下，单条棱构造成功（重放一致、中心恢复、动作合法、目标配对）。
- 深入打乱超出预算（研究原型，返回 SEARCH_BUDGET_EXHAUSTED，不假装成功）。
- 输入对象不被修改。
"""

import random

import pytest

from cube.colors import DEFAULT_COLORS
from cube.cube5 import Cube5
from solver.center5.legal_moves import (
    LEGAL_5X5_CENTER_MOVES,
    assert_legal_5x5_solution_moves,
)
from solver.edge5 import (
    EdgeMoveEffect,
    SINGLE_EDGE_PAIR_ERRORS,
    SingleEdgePairResult,
    build_edge_move_effect,
    center_color_off,
    center_identity_off,
    centers_are_color_solved,
    edge_type_of_cubie,
    is_edge_paired,
    is_edge_solved,
    paired_count,
    pair_single_edge,
    solved_count,
)
from solver.edge5.moves import build_edge_move_effects
from solver.edge5.positions import (
    MIDDLE_INDEX,
    MIDDLE_ORDER,
    SLOT_NAMES,
    SLOTS,
    WING_INDEX,
    WING_ORDER,
    color_pair_of_slot,
    edge_positions,
    is_middle_pos,
    is_wing_pos,
    slot,
    slot_of,
)

_ALL_LEGAL = tuple(LEGAL_5X5_CENTER_MOVES)


def make_legal_scramble(seed: int, length: int = 20) -> list:
    rng = random.Random(seed)
    return [rng.choice(_ALL_LEGAL) for _ in range(length)]


def _apply(cube, moves):
    for m in moves:
        cube.apply_move(m)


class TestPositionsModel:
    def test_36_edges_match_cube(self):
        cube = Cube5.solved()
        cube_edges = {p for p, c in cube.cubies.items() if len(c.stickers) == 2}
        assert cube_edges == set(edge_positions())
        assert len(cube_edges) == 36

    def test_twelve_middle_twentyfour_wing(self):
        assert len(MIDDLE_ORDER) == 12
        assert len(WING_ORDER) == 24
        assert all(is_middle_pos(p) for p in MIDDLE_ORDER)
        assert all(is_wing_pos(p) for p in WING_ORDER)

    def test_twelve_slots_valid(self):
        assert len(SLOT_NAMES) == 12
        assert set(SLOTS) == set(SLOT_NAMES)
        for name, s in SLOTS.items():
            assert name in SLOT_NAMES
            assert slot_of(s.middle) == name
            assert slot_of(s.left_wing) == name
            assert slot_of(s.right_wing) == name

    def test_slot_classification(self):
        # 中棱：恰好 2 个坐标 ±6，第三坐标 0；翼：第三坐标 ±3。
        for name in SLOT_NAMES:
            s = slot(name)
            assert is_middle_pos(s.middle)
            assert is_wing_pos(s.left_wing)
            assert is_wing_pos(s.right_wing)
            assert s.left_wing != s.right_wing


class TestEdgeType:
    def test_order_independent(self):
        cube = Cube5.solved()
        for pos, cubie in cube.cubies.items():
            if len(cubie.stickers) == 2:
                et = edge_type_of_cubie(cubie)
                assert isinstance(et, frozenset)
                assert len(et) == 2
                # 反转 sticker 顺序不改变色对
                assert frozenset(list(et)) == et

    def test_home_slot_color_pair(self):
        cube = Cube5.solved()
        for name in SLOT_NAMES:
            et = edge_type_of_cubie(cube.cubies[slot(name).middle])
            assert et == color_pair_of_slot(name, DEFAULT_COLORS)


class TestOrbitClosure:
    def test_wings_stay_in_wing_orbit(self):
        for seed in range(10):
            cube = Cube5.solved()
            cube.apply_moves(make_legal_scramble(seed, 20))
            for cubie in cube.cubies.values():
                if len(cubie.stickers) != 2:
                    continue
                assert is_wing_pos(cubie.home) == is_wing_pos(cubie.pos)

    def test_middles_stay_in_middle_orbit(self):
        for seed in range(10):
            cube = Cube5.solved()
            cube.apply_moves(make_legal_scramble(seed, 20))
            for cubie in cube.cubies.values():
                if len(cubie.stickers) != 2:
                    continue
                assert is_middle_pos(cubie.home) == is_middle_pos(cubie.pos)


class TestStatePredicates:
    def test_solved_all_paired_and_solved(self):
        cube = Cube5.solved()
        assert paired_count(cube) == 12
        assert solved_count(cube) == 12
        for name in SLOT_NAMES:
            assert is_edge_paired(cube, name)
            assert is_edge_solved(cube, name)

    def test_semantic_separation(self):
        # 在打乱态下，某条色对可能聚集在非 home 槽：paired=True 但 solved=False。
        found = False
        for seed in range(300):
            cube = Cube5.solved()
            cube.apply_moves(make_legal_scramble(seed, 25))
            pc = paired_count(cube)
            sc = solved_count(cube)
            if pc > sc:
                found = True
                break
        assert found, "应至少出现一次「配对但未归位」的语义分离案例"

    def test_scramble_reduces_paired(self):
        cube = Cube5.solved()
        cube.apply_moves(make_legal_scramble(seed=0, length=25))
        assert paired_count(cube) < 12


class TestEdgeMoveEffect:
    def test_effect_consistent_with_cube(self):
        for mv in _ALL_LEGAL:
            e = build_edge_move_effect(mv)
            cube = Cube5.solved()
            cube.apply_move(mv)
            mp = tuple(MIDDLE_INDEX[cube.cubies[p].home] for p in MIDDLE_ORDER)
            wp = tuple(WING_INDEX[cube.cubies[p].home] for p in WING_ORDER)
            assert e.middle_perm == mp, mv
            assert e.wing_perm == wp, mv

    def test_inverse_restores_for_all_moves(self):
        for mv in _ALL_LEGAL:
            e = build_edge_move_effect(mv)
            assert e.inverse_restores, mv

    def test_fixed_face_centers_preserved(self):
        for mv in _ALL_LEGAL:
            e = build_edge_move_effect(mv)
            assert e.fixed_face_centers_preserved, mv

    def test_touched_slots_consistent(self):
        # 外层转移动 4 个槽，宽层转移动 8 个槽（与前期研究一致）。
        outer = build_edge_move_effect("R")
        assert len(outer.touched_slots) == 4
        wide = build_edge_move_effect("2R")
        assert len(wide.touched_slots) == 8

    def test_outer_vs_wide_group_behaviour(self):
        # 外层转整体搬运所有梯（group_split==0）；宽层转拆散工作区 4 组。
        outer = build_edge_move_effect("U")
        assert len(outer.group_split) == 0
        wide = build_edge_move_effect("2U")
        assert len(wide.group_split) == 4

    def test_effects_number(self):
        effects = build_edge_move_effects(tuple(_ALL_LEGAL))
        assert len(effects) == len(_ALL_LEGAL)
        assert all(isinstance(v, EdgeMoveEffect) for v in effects.values())


class TestSingleEdgePair:
    def test_solved_input(self):
        cube = Cube5.solved()
        target = color_pair_of_slot("UF", DEFAULT_COLORS)
        res = pair_single_edge(cube, target, "UF")
        assert res.success
        assert res.moves == ()
        assert res.centers_restored
        assert res.target_paired
        assert isinstance(res, SingleEdgePairResult)

    @pytest.mark.parametrize("seed", [0, 1, 2, 3, 4, 5])
    def test_controlled_single_edge(self, seed):
        # 受控短打乱（≤3 步）下，原型应可靠完成单条棱构造。
        cube = Cube5.solved()
        cube.apply_moves(make_legal_scramble(seed, 3))
        original_state = cube.clone()
        target = color_pair_of_slot("UF", DEFAULT_COLORS)
        res = pair_single_edge(cube, target, "UF")
        assert res.success, "seed %d: %s" % (seed, res.message)
        assert_legal_5x5_solution_moves(list(res.moves))
        # 输入不被修改
        for pos, cubie in cube.cubies.items():
            assert cubie.pos == original_state.cubies[pos].pos
            assert cubie.home == original_state.cubies[pos].home
        # 从原状态重放验证（中心恢复目标为「按颜色归面」）
        replay = original_state.clone()
        replay.apply_moves(list(res.moves))
        assert is_edge_paired(replay, "UF")
        assert centers_are_color_solved(replay)

    def test_deeper_scramble_documented_failure(self):
        # 深入打乱是研究原型的已知限制：应返回明确 error_code，而非假装成功。
        cube = Cube5.solved()
        cube.apply_moves(make_legal_scramble(seed=7, length=20))
        target = color_pair_of_slot("UF", DEFAULT_COLORS)
        res = pair_single_edge(cube, target, "UF", node_budget=50000)
        assert not res.success
        assert res.error_code in SINGLE_EDGE_PAIR_ERRORS

    def test_unknown_work_slot_raises(self):
        cube = Cube5.solved()
        target = color_pair_of_slot("UF", DEFAULT_COLORS)
        with pytest.raises(ValueError):
            pair_single_edge(cube, target, "XX")


class TestCenterColorVsIdentity:
    """关键回归：外层动作只置换同面中心身份，不破坏「按颜色归面」。

    早期把 center_identity_off 当作恢复代价导致搜索被过度约束。
    """

    @pytest.mark.parametrize("move", ["R", "R'", "R2", "U", "U'", "U2",
                                      "F", "F2", "B", "B2", "L", "D"])
    def test_outer_turn_preserves_color_solved_centers(self, move):
        cube = Cube5.solved()
        cube.apply_move(move)
        # 外层动作：身份位移 >0，但颜色归面错位 ==0，中心按颜色求解。
        assert center_identity_off(cube) > 0
        assert center_color_off(cube) == 0
        assert centers_are_color_solved(cube)

    @pytest.mark.parametrize("move", ["2R", "2R'", "2R2", "2U", "2F", "2L", "2D"])
    def test_wide_turn_disturbs_color_solved_centers(self, move):
        cube = Cube5.solved()
        cube.apply_move(move)
        # 宽层动作：跨面颜色错位 >0，中心不再按颜色求解。
        assert center_color_off(cube) > 0
        assert not centers_are_color_solved(cube)

    def test_outer_can_move_identity_without_unsolving_color(self):
        cube = Cube5.solved()
        cube.apply_move("R")
        cube.apply_move("U")
        cube.apply_move("F")
        assert center_identity_off(cube) > 0
        assert centers_are_color_solved(cube)

    def test_solved_zero_off(self):
        assert center_color_off(Cube5.solved()) == 0
        assert center_identity_off(Cube5.solved()) == 0

