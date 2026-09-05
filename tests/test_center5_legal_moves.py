"""5x5 求解器合法动作与固定面心不变量测试。

标准实体 5x5 的六个面心是固定参考件，合法动作（外层 + 两层宽转）不得置换它们。
3/4/5 层宽转会经过中面，从而非法移动四个面心，求解器边界必须拒绝。
"""

import random

import pytest

from cube.cube5 import Cube5
from solver.center5 import (
    LEGAL_5X5_CENTER_MOVES,
    IllegalMoveForCube5Solver,
    assert_legal_5x5_solution_moves,
    compute_center_orbits,
    invert_move_string,
    is_legal_5x5_solver_move,
)

# 六个固定面心的 home（身份参考）
FIXED_CENTER_HOME_POSITIONS = (
    (6, 0, 0), (-6, 0, 0),
    (0, 6, 0), (0, -6, 0),
    (0, 0, 6), (0, 0, -6),
)


def fixed_center_piece_positions(cube):
    """返回固定面心 cubie 的当前坐标；若身份被破坏则返回 None。"""
    out = []
    for home in FIXED_CENTER_HOME_POSITIONS:
        cubie = cube.cubie_at(home)
        if cubie is None or cubie.home != home or cubie.pos != home:
            return None
        out.append(cubie.pos)
    return tuple(out)


# ---------------------------------------------------------------------------
# 合法动作定义
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("move", LEGAL_5X5_CENTER_MOVES)
def test_legal_solver_moves_are_accepted(move):
    assert is_legal_5x5_solver_move(move)


@pytest.mark.parametrize("move", ["3F", "3F'", "4R", "5U", "3R2", "4B"])
def test_middle_crossing_moves_are_rejected_for_5x5_solver(move):
    assert not is_legal_5x5_solver_move(move)


def test_whole_cube_and_invalid_rejected():
    for move in ["x", "y", "z", "x2", "", "Q", "Rw"]:
        assert not is_legal_5x5_solver_move(move)


def test_legal_set_only_contains_outer_and_two_layer():
    for move in LEGAL_5X5_CENTER_MOVES:
        assert move[0] in ("R", "L", "U", "D", "F", "B", "2")


@pytest.mark.parametrize("move", ["3F", "4R", "5U", "x"])
def test_assert_legal_raises_on_illegal(move):
    with pytest.raises(IllegalMoveForCube5Solver):
        assert_legal_5x5_solution_moves(["2R", move])


def test_assert_legal_ok_on_legal():
    assert_legal_5x5_solution_moves(["R", "2R", "U2", "2B'"])


# ---------------------------------------------------------------------------
# 记号歧义: R2 外层 180, 2R 宽层 90, 2R2 宽层 180
# ---------------------------------------------------------------------------

def test_notation_ambiguity_R2_vs_2R_vs_2R2():
    assert invert_move_string("R2") == "R2"
    assert invert_move_string("2R") == "2R'"
    assert invert_move_string("2R2") == "2R2"
    assert invert_move_string("2R'") == "2R"
    assert invert_move_string("U") == "U'"


# ---------------------------------------------------------------------------
# 固定面心不变量：单动作
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("move", LEGAL_5X5_CENTER_MOVES)
def test_legal_move_preserves_fixed_face_centers(move, solved_5x5):
    before = fixed_center_piece_positions(solved_5x5)
    solved_5x5.apply_move(move)
    assert fixed_center_piece_positions(solved_5x5) == before
    assert before is not None


# ---------------------------------------------------------------------------
# 固定面心不变量：动作与逆动作
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("move", LEGAL_5X5_CENTER_MOVES)
def test_legal_move_and_inverse_restore_cube(move, solved_5x5):
    original = solved_5x5.clone()
    solved_5x5.apply_moves([move, invert_move_string(move)])
    assert solved_5x5.is_solved()


# ---------------------------------------------------------------------------
# 固定面心不变量：随机合法序列（固定种子）
# ---------------------------------------------------------------------------

def test_random_legal_sequences_preserve_fixed_face_centers(solved_5x5):
    rng = random.Random(501)
    for _ in range(100):
        cube = solved_5x5.clone()
        moves = [rng.choice(LEGAL_5X5_CENTER_MOVES) for _ in range(50)]
        cube.apply_moves(moves)
        assert fixed_center_piece_positions(cube) == FIXED_CENTER_HOME_POSITIONS


def test_random_legal_sequences_do_not_move_any_face_center(solved_5x5):
    rng = random.Random(502)
    for _ in range(50):
        cube = solved_5x5.clone()
        moves = [rng.choice(LEGAL_5X5_CENTER_MOVES) for _ in range(40)]
        cube.apply_moves(moves)
        assert fixed_center_piece_positions(cube) == FIXED_CENTER_HOME_POSITIONS


# ---------------------------------------------------------------------------
# 轨道断言
# ---------------------------------------------------------------------------

def test_legal_center_orbits_are_two_24_plus_six_singletons():
    orbits = compute_center_orbits(LEGAL_5X5_CENTER_MOVES)
    assert sorted(map(len, orbits)) == [1, 1, 1, 1, 1, 1, 24, 24]


def test_each_legal_move_preserves_center_orbit_membership(solved_5x5):
    from solver.center5.orbits import (
        center_positions, compute_center_orbits, kind_of_position,
    )
    orbits = compute_center_orbits(LEGAL_5X5_CENTER_MOVES)
    # 轨道成员始终保持归属（用固定面心身份校验 + 重放一致性）
    fixed_set = set(FIXED_CENTER_HOME_POSITIONS)
    assert set(center_positions(5)) & fixed_set == fixed_set
    for move in LEGAL_5X5_CENTER_MOVES:
        cube = Cube5.solved()
        cube.apply_move(move)
        # 每个固定面心仍在固定面心位置
        assert fixed_center_piece_positions(cube) == FIXED_CENTER_HOME_POSITIONS
        # 每个活动中心仍在活动位置（位置坐标不变集合）
        for home in center_positions(5):
            if home not in fixed_set:
                cubie = cube.cubie_at(home)
                assert cubie is not None
                assert kind_of_position(cubie.home) == kind_of_position(home)
