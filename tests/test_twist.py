"""测试拧魔方（renderer.twist）的解析与应用逻辑。"""

import pytest

from cube.coordinates import get_d_maxc, FACE_AXIS_SIGN, coord_values
from cube.cube2 import Cube2
from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.cube5 import Cube5
from cube.conversion import cubies_to_facelets, facelets_to_cubies
from renderer.twist import (
    resolve_twist, apply_layer_turn, ROT_PLUS, _wide_positions,
)

_CLS = {2: Cube2, 3: Cube3, 4: Cube4, 5: Cube5}


def _front_basis():
    """正对普通 3D 视角：eye 在 +Z，looking 原点。"""
    return {
        "basis": ((0.0, 0.0, 9.0), (1.0, 0.0, 0.0),
                  (0.0, 1.0, 0.0), (0.0, 0.0, -1.0)),
        "pixel_scale": 1.0,
        "center_x": 0.0,
        "center_y": 0.0,
        "wcx": 0.0,
        "wcy": 0.0,
    }


def _clone_cube(cube):
    return {p: c.clone() for p, c in cube.cubies.items()}


def _same_positions(a, b):
    return all(a[p].pos == b[p].pos for p in a)


# --------------------------------------------------------------------------
# apply_layer_turn vs 引擎
# --------------------------------------------------------------------------
@pytest.mark.parametrize("n", [2, 3, 4, 5])
@pytest.mark.parametrize("face", ["R", "L", "U", "D", "F", "B"])
def test_apply_layer_turn_matches_engine(n, face):
    cls = _CLS[n]
    d, maxc = get_d_maxc(n)
    axis = FACE_AXIS_SIGN[face][0]
    sign_face = FACE_AXIS_SIGN[face][1]
    slab = sign_face * maxc
    # 正法线面是右手 -90（sign=-1），负法线面是右手 +90（sign=+1）。
    sign = -1 if sign_face > 0 else 1

    c = cls.solved()
    cub = _clone_cube(c)
    apply_layer_turn(cub, axis, [slab], sign)

    c2 = cls.solved()
    c2.apply_move(face)
    assert _same_positions(cub, c2.cubies)


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_apply_layer_turn_preserves_home(n):
    cls = _CLS[n]
    _, maxc = get_d_maxc(n)
    c = cls.solved()
    cub = _clone_cube(c)
    before = {id(cc): cc.home for cc in cub.values()}
    apply_layer_turn(cub, 0, [maxc], -1)
    for cc in cub.values():
        assert cc.home == before[id(cc)]


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_apply_layer_turn_invert_returns_solved(n):
    cls = _CLS[n]
    _, maxc = get_d_maxc(n)
    c = cls.solved()
    cub = _clone_cube(c)
    apply_layer_turn(cub, 0, [maxc], -1)
    apply_layer_turn(cub, 0, [maxc], 1)
    assert _same_positions(cub, c.cubies)


def test_rotate_plus_is_right_hand_90_about_each_axis():
    # 绕 +X 右手 +90：+Y -> +Z
    assert ROT_PLUS[0](0, 1, 0) == (0, 0, 1)
    # 绕 +Y 右手 +90：+Z -> +X
    assert ROT_PLUS[1](0, 0, 1) == (1, 0, 0)
    # 绕 +Z 右手 +90：+X -> +Y
    assert ROT_PLUS[2](1, 0, 0) == (0, 1, 0)


# --------------------------------------------------------------------------
# resolve_twist
# --------------------------------------------------------------------------
def test_resolve_twist_front_drag_right():
    p = _front_basis()
    spec = resolve_twist(
        3, p["basis"], p["pixel_scale"], p["center_x"], p["center_y"],
        p["wcx"], p["wcy"], (10, 0), (0, 0), wide=False)
    assert spec is not None
    assert spec.axis == 1          # Y：把正面中心往右移动
    assert spec.sign == 1
    assert spec.layer_positions == [0]


def test_resolve_twist_front_drag_up():
    p = _front_basis()
    spec = resolve_twist(
        3, p["basis"], p["pixel_scale"], p["center_x"], p["center_y"],
        p["wcx"], p["wcy"], (0, 10), (0, 0), wide=False)
    assert spec is not None
    assert spec.axis == 0          # X：把正面中心向上抬
    assert spec.sign == -1


def test_resolve_twist_returns_none_when_no_hit():
    # 抓取点偏离魔方，射线不命中。
    p = _front_basis()
    spec = resolve_twist(
        3, p["basis"], p["pixel_scale"], p["center_x"], p["center_y"],
        p["wcx"], p["wcy"], (10, 0), (1000, 1000), wide=False)
    assert spec is None


def test_wide_positions_merges_outer_and_inner():
    # 抓最外层时并入相邻同侧内层；非最外层 / 无内层时保持原层。
    for n in (3, 4, 5):
        _, maxc = get_d_maxc(n)
        vals = coord_values(n)
        inners = [v for v in vals if 0 < v < maxc]
        if inners:
            inner = max(inners)
            assert _wide_positions(n, 0, maxc) == sorted([maxc, inner])
            assert _wide_positions(n, 1, -maxc) == sorted([-maxc, -inner])
        else:
            assert _wide_positions(n, 0, maxc) == [maxc]
        # 非最外层（如中层，若存在）不加内层。
        if 0 in vals:
            assert _wide_positions(n, 2, 0) == [0]


def test_roundtrip_facelets_through_layer_turn_matches_engine():
    """facelets -> cubies -> 层转动 -> facelets 与引擎同名转动一致。"""
    n = 3
    _, maxc = get_d_maxc(n)
    cube = Cube3.solved()
    fl = cubies_to_facelets(cube.cubies, n)

    cub = facelets_to_cubies(fl, n)
    apply_layer_turn(cub, 0, [maxc], -1)   # = R
    out = cubies_to_facelets(cub, n)

    c2 = Cube3.solved()
    c2.apply_move("R")
    assert out == cubies_to_facelets(c2.cubies, n)


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_roundtrip_preserves_empty_stickers(n):
    """未填色（空串）小面在互转闭环后仍保留：无丢失、无增色。"""
    cls = _CLS[n]
    _, maxc = get_d_maxc(n)
    cube = cls.solved()
    fl = cubies_to_facelets(cube.cubies, n)
    # 仅保留部分小面，其余置空串。
    keep = {"U": 0, "R": 1}
    for face in fl:
        for r in range(n):
            for c in range(n):
                if (face, (r + c) % 2) not in ((k, v) for k, v in keep.items()):
                    fl[face][r][c] = ""
    # 空串在转换中无丢失。
    cub = facelets_to_cubies(fl, n)
    assert cubies_to_facelets(cub, n) == fl

    # 层转动后无丢失：非空小面数量不变。
    cub2 = facelets_to_cubies(fl, n)
    apply_layer_turn(cub2, 0, [maxc], -1)   # = R（外层）
    out = cubies_to_facelets(cub2, n)
    def n_filled(f):
        return sum(1 for face in f.values() for row in face for v in row if v)
    assert n_filled(out) == n_filled(fl)
