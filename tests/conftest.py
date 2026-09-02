"""共享 fixtures 与辅助函数。"""

import random

import pytest

from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.conversion import cubies_to_facelets
from cube.coordinates import FACE_AXIS_SIGN, rc_from_pos
from cube.notation import (
    inverse_move,
    parse_algorithm,
    parse_move_str,
    suffix_for_count,
)

# 3x3 面转动（不含 x/y/z，保持中心不动，便于校验测试）
FACES_3X3 = ["R", "L", "U", "D", "F", "B"]
FACES_4X4 = ["R", "L", "U", "D", "F", "B"]
SUFFIXES = ["", "'", "2", "3"]


def clone_facelets(facelets):
    return {f: [row[:] for row in grid] for f, grid in facelets.items()}


def swap_cells(facelets, fa, ra, ca, fb, rb, cb):
    """交换两个格子颜色。"""
    tmp = facelets[fa][ra][ca]
    facelets[fa][ra][ca] = facelets[fb][rb][cb]
    facelets[fb][rb][cb] = tmp


def random_scramble(rng, n, wide=False, length=20):
    """生成随机面转动序列（含逆/180/270）。"""
    moves = []
    for _ in range(length):
        face = rng.choice(FACES_3X3 if n == 3 else FACES_4X4)
        suffix = rng.choice(SUFFIXES)
        base = face.lower() if (wide and n == 4) else face
        moves.append(base + suffix)
    return moves


def move_to_parseable(move):
    """Move 三元组 -> 可被 parse_move_str 解析的字符串。

    宽层用小写面标签（如 "r"），x/y/z 保持原样。
    """
    label, is_wide, count = move
    if label in ("x", "y", "z"):
        base = label
    elif is_wide:
        base = label.lower()
    else:
        base = label
    return base + suffix_for_count(count)


def inverse_scramble(moves):
    """给定动作字符串序列，返回逆序列（可被 apply_moves 解析）。"""
    inv = []
    for s in reversed(list(moves)):
        inv.append(move_to_parseable(inverse_move(parse_move_str(s))))
    return inv


def faces_of(pos):
    """根据非零坐标，返回该位置立方块所接触的面（有序）。"""
    faces = []
    for axis in (0, 1, 2):
        v = pos[axis]
        if v != 0:
            sign = 1 if v > 0 else -1
            for f, (ax, sn) in FACE_AXIS_SIGN.items():
                if ax == axis and sn == sign:
                    faces.append(f)
    return faces


@pytest.fixture
def rng():
    return random.Random(20240827)


@pytest.fixture
def solved_3x3():
    return Cube3.solved()


@pytest.fixture
def solved_3x3_facelets():
    cube = Cube3.solved()
    return cubies_to_facelets(cube.cubies, 3)


@pytest.fixture
def solved_4x4():
    return Cube4.solved()


@pytest.fixture
def solved_4x4_facelets():
    cube = Cube4.solved()
    return cubies_to_facelets(cube.cubies, 4)


@pytest.fixture
def scramble_3x3_moves(rng):
    return random_scramble(rng, 3, length=30)
