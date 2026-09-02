"""3x3 求解器端到端测试（依赖 kociemba-src 预生成的 twophase 表）。

solver3 通过 import 时加载 ~63 MB 表（冷启动成本在此付一次），
因此这里测的是热启动性能与正确性。
"""

import pytest

from cube.facelet_model import FaceletCube
from solver import solve_3x3

# hkociemba 只输出 URFDLB 面转动，天然不含 x/y/z；此集合用于强约束校验。
_FACE_MOVES_ONLY = set("URFDLB")


def _clone(facelets):
    return {f: [row[:] for row in grid] for f, grid in facelets.items()}


def _scrambled(solved_facelets, moves):
    cube = FaceletCube(_clone(solved_facelets), 3)
    cube.apply_moves(moves)
    return cube, cube.facelets


def test_solved_cube_zero_moves(solved_3x3_facelets):
    result = solve_3x3(solved_3x3_facelets)
    assert result.success is True
    assert result.moves == []
    assert result.move_count == 0


def test_scrambled_cube_solves_correctly(solved_3x3_facelets, scramble_3x3_moves):
    _, scrambled = _scrambled(solved_3x3_facelets, scramble_3x3_moves)

    result = solve_3x3(scrambled)
    assert result.success is True
    assert 0 < result.move_count <= 50

    # 把求解结果套回打乱后的状态，必须复原
    verify = FaceletCube(_clone(scrambled), 3)
    verify.apply_moves(result.moves)
    assert verify.is_solved()


def test_moves_use_only_face_turns(solved_3x3_facelets, scramble_3x3_moves):
    _, scrambled = _scrambled(solved_3x3_facelets, scramble_3x3_moves)
    result = solve_3x3(scrambled)
    assert result.success is True
    for mv in result.moves:
        base = mv.rstrip("2'3")
        assert base in _FACE_MOVES_ONLY, f"unexpected move {mv}"


def test_hot_solve_timing(solved_3x3_facelets, scramble_3x3_moves):
    _, scrambled = _scrambled(solved_3x3_facelets, scramble_3x3_moves)
    # import 已完成冷加载，此处计时即热启动耗时
    result = solve_3x3(scrambled)
    assert result.success is True
    assert result.elapsed_ms < 5000


def test_result_structure(solved_3x3_facelets, scramble_3x3_moves):
    _, scrambled = _scrambled(solved_3x3_facelets, scramble_3x3_moves)
    result = solve_3x3(scrambled)
    assert result.success is True
    assert result.move_count == len(result.moves)
    assert result.elapsed_ms >= 0
    assert result.message.startswith("Error") is False
