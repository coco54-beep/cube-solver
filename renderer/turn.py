"""把动作字符串转换为转动动画参数。

动作 (label, wide, count) -> 若干 MoveStep（每个代表一次 90° 整层转动）。

坐标约定（见 cube/coordinates）：
    R/L 绕 X 轴，U/D 绕 Y 轴，F/B 绕 Z 轴。
外层转动作用于 ±maxc 层；宽层 (wide) 额外作用 ±(maxc - d)。
3x3 无宽层（wide 等价基础）。
"""

import math

from cube.notation import parse_move_str
from cube.coordinates import get_d_maxc, TURNS

_AXIS = {"R": 0, "L": 0, "U": 1, "D": 1, "F": 2, "B": 2}
_AXIS_VEC = {0: (1, 0, 0), 1: (0, 1, 0), 2: (0, 0, 1)}

# 面层符号
_SIGN = {"R": 1, "L": -1, "U": 1, "D": -1, "F": 1, "B": -1}


def _quarter_angle(base: str, ccw: bool) -> float:
    """基准 base 的顺时针 90° 带符号角度。

    通过旋转参考向量并与轴向量叉积求符号，保证与 TURNS 一致。
    axis: 0/1/2，向量取该轴正方向为参考。
    """
    axis = _AXIS[base]
    av = _AXIS_VEC[axis]
    # 取一个垂直于轴的参考向量
    ref = (0, 0, 1) if axis != 2 else (1, 0, 0)
    rot = TURNS[base]
    if ccw:
        # 逆时针 = 顺时针 3 次
        r = ref
        for _ in range(3):
            r = rot(*r)
    else:
        r = rot(*ref)

    # 计算 ref 转到 r 的带符号角（绕轴 av）
    # 用叉积的轴向分量判断方向
    rx, ry, rz = ref
    nx, ny, nz = r
    cx = ry * nz - rz * ny
    cy = rz * nx - rx * nz
    cz = rx * ny - ry * nx
    dot = av[0] * cx + av[1] * cy + av[2] * cz
    return 90.0 if dot > 0 else -90.0


class MoveStep:
    """一次动画步骤：一次整层转动（可为 90/180/270 度，含宽层）。"""

    __slots__ = ("base", "axis", "layers", "angle", "count", "wide", "ccw", "move_str")

    def __init__(self, base, axis, layers, angle, count, wide, ccw, move_str):
        self.base = base
        self.axis = axis
        self.layers = layers
        self.angle = angle
        self.count = count
        self.wide = wide
        self.ccw = ccw
        self.move_str = move_str


def decompose_move(move_str, n):
    """把一条动作分解为单个 MoveStep（一次转动，角度 = 单次90°×次数）。

    180 / 270 度不拆成多个 90°，而是作为一次动画转完，
    避免中间 set_cube 造成的颜色跳变。
    """
    label, is_wide, count = parse_move_str(move_str)
    base = label
    ccw = (count == 3)
    d, maxc = get_d_maxc(n)
    axis = _AXIS[base]
    sign = _SIGN[base]
    layers = [sign * maxc]
    if is_wide and n > 3:
        layers.append(sign * (maxc - d))
    layers = tuple(sorted(set(layers), key=abs))
    per = _quarter_angle(base, ccw)
    # 动画一次转的角度：90/180 转实际角度；270 只用一次 90°（逆时针），
    # 与 3 次顺时针 90° 最终的矩阵朝向一致（避免转 -270 的方向错位）。
    angle = per if count == 3 else per * count
    return [MoveStep(base, axis, layers, angle, count, is_wide, ccw, move_str)]
