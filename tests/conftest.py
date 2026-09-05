"""共享 fixtures 与辅助函数。"""

import random

import pytest

from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.cube5 import Cube5
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
FACES_5X5 = ["R", "L", "U", "D", "F", "B", "2R", "2L", "2U", "2D", "2F", "2B"]
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
    pool = FACES_3X3 if n == 3 else (FACES_5X5 if n == 5 else FACES_4X4)
    for _ in range(length):
        face = rng.choice(pool)
        suffix = rng.choice(SUFFIXES)
        if n == 5:
            base = face
        else:
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
    """给定动作字符串序列，返回逆序列（可被 apply_moves 解析）。

    支持任意层数前缀（如 "2R"/"3R"），通过 parse_move_full 解析并重建。
    """
    from cube.notation import parse_move_full

    def inv_one(s):
        label, layers, count = parse_move_full(s)
        inv_count = (4 - count) % 4
        suffix = suffix_for_count(inv_count)
        if label in ("x", "y", "z"):
            return label + suffix
        prefix = str(layers) if layers != 1 else ""
        return prefix + label + suffix

    return [inv_one(s) for s in reversed(list(moves))]


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
def solved_5x5():
    return Cube5.solved()


@pytest.fixture
def solved_5x5_facelets():
    cube = Cube5.solved()
    return cubies_to_facelets(cube.cubies, 5)


@pytest.fixture
def scramble_3x3_moves(rng):
    return random_scramble(rng, 3, length=30)
