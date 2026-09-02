"""统一坐标系与转动旋转公式。

坐标系（右手系）：
    X轴正方向: R   X轴负方向: L
    Y轴正方向: U   Y轴负方向: D
    Z轴正方向: F   Z轴负方向: B

坐标取值（离散整数）：
    3x3: {-1, 0, 1}        (d=1, maxc=1)
    4x4: {-3, -1, 1, 3}    (d=2, maxc=3)
    公式: maxc = (n-1)*d//2,  coord(i) = (2*i-(n-1))*d//2

FACE_SPEC 每面的 (n_axis, n_sign, row_axis, row_sign, col_axis, col_sign)：
    n_axis:   该面法线所在轴
    n_sign:   该面所在层的法线符号 (+maxc)
    row_axis: 网格行 r 对应轴,  row_sign: 行符号
    col_axis: 网格列 c 对应轴,  col_sign: 列符号

FACE_NORMALS: 面法线向量（用于 sticker 方向键）。
TURNS: 各面顺时针90度转动的坐标旋转公式。
WHOLE_CUBE: x/y/z 整体转动复用哪一面的旋转公式。
"""

from typing import List, Tuple

Coord = Tuple[int, int, int]

# 轴索引: 0=X, 1=Y, 2=Z

# 每面网格 -> 3D 坐标映射
FACE_SPEC = {
    "F": (2, +1, 1, -1, 0, +1),
    "U": (1, +1, 2, +1, 0, +1),
    "D": (1, -1, 2, -1, 0, +1),
    "B": (2, -1, 1, -1, 0, -1),
    "R": (0, +1, 1, -1, 2, -1),
    "L": (0, -1, 1, -1, 2, +1),
}

# 面法线向量
FACE_NORMALS = {
    "F": (0, 0, +1),
    "U": (0, +1, 0),
    "D": (0, -1, 0),
    "B": (0, 0, -1),
    "R": (+1, 0, 0),
    "L": (-1, 0, 0),
}

# 面 -> (法线轴, 法线符号)
FACE_AXIS_SIGN = {
    "F": (2, +1),
    "U": (1, +1),
    "D": (1, -1),
    "B": (2, -1),
    "R": (0, +1),
    "L": (0, -1),
}


def get_d_maxc(n: int) -> Tuple[int, int]:
    """返回 (d, maxc)。3x3 -> (1,1); 4x4 -> (2,3)。"""
    d = n - 2
    maxc = (n - 1) * d // 2
    return d, maxc


def coord_values(n: int) -> List[int]:
    """返回该阶坐标取值列表。"""
    d, _ = get_d_maxc(n)
    return [(2 * i - (n - 1)) * d // 2 for i in range(n)]


def pos_from_rc(n: int, face: str, r: int, c: int) -> Coord:
    """面网格坐标 (r, c) -> 3D 坐标。r, c 均从 0 开始。"""
    n_axis, n_sign, row_axis, row_sign, col_axis, col_sign = FACE_SPEC[face]
    vals = coord_values(n)
    d, maxc = get_d_maxc(n)
    pos = [0, 0, 0]
    pos[n_axis] = n_sign * maxc
    pos[row_axis] = vals[r] * row_sign
    pos[col_axis] = vals[c] * col_sign
    return (pos[0], pos[1], pos[2])


def rc_from_pos(n: int, face: str, pos: Coord) -> Tuple[int, int]:
    """3D 坐标 -> 面网格坐标 (r, c)。要求 pos[n_axis]==n_sign*maxc。"""
    n_axis, n_sign, row_axis, row_sign, col_axis, col_sign = FACE_SPEC[face]
    d, _ = get_d_maxc(n)
    # r = round((n-1)/2 + pos[row_axis]/(d*row_sign))
    r = round((n - 1) / 2 + pos[row_axis] / (d * row_sign))
    c = round((n - 1) / 2 + pos[col_axis] / (d * col_sign))
    return (r, c)


def layer_values(n: int, face: str, is_wide: bool = False) -> List[int]:
    """返回该面转动所作用层的法线轴坐标值集合。

    基础面转动: {n_sign*maxc}
    宽层转动 (仅 n>3): {n_sign*maxc, n_sign*(maxc-d)}
    3x3 宽层 == 基础（3阶只有单层）。
    """
    n_axis, n_sign = FACE_AXIS_SIGN[face]
    d, maxc = get_d_maxc(n)
    if is_wide and n > 3:
        return [n_sign * maxc, n_sign * (maxc - d)]
    return [n_sign * maxc]


def is_in_layer(n: int, face: str, is_wide: bool, pos: Coord) -> bool:
    """判断 pos 是否属于该面（基础/宽层）转动层。"""
    n_axis, n_sign = FACE_AXIS_SIGN[face]
    d, maxc = get_d_maxc(n)
    if is_wide and n > 3:
        return pos[n_axis] in (n_sign * maxc, n_sign * (maxc - d))
    return pos[n_axis] == n_sign * maxc


# ---------------------------------------------------------------------------
# 转动旋转公式
# ---------------------------------------------------------------------------
# 各面顺时针90度（正对该面观察）的坐标旋转。
# 已通过旋转矩阵 + 角块循环 + 边块行为三重验证。

TURNS = {
    "R": lambda x, y, z: (x, z, -y),
    "L": lambda x, y, z: (x, -z, y),
    "U": lambda x, y, z: (-z, y, x),
    "D": lambda x, y, z: (z, y, -x),
    "F": lambda x, y, z: (y, -x, z),
    "B": lambda x, y, z: (-y, x, z),
}

# 逆转动（逆时针90度）复用另一面的旋转公式：
#   R' 与 L 共享 (x,-z,y); L' 与 R 共享 (x,z,-y)
#   U' 与 D 共享 (z,y,-x); D' 与 U 共享 (-z,y,x)
#   F' 与 B 共享 (-y,x,z); B' 与 F 共享 (y,-x,z)
# 注意：作用于不同层（R' 作用于 x=+maxc，L 作用于 x=-maxc）。
INVERSE_TURNS = {
    "R": TURNS["L"],
    "L": TURNS["R"],
    "U": TURNS["D"],
    "D": TURNS["U"],
    "F": TURNS["B"],
    "B": TURNS["F"],
}

# 整体转动 x/y/z 复用哪一面的旋转公式：
#   x (绕X轴) -> R 的旋转
#   y (绕Y轴) -> U 的旋转
#   z (绕Z轴) -> F 的旋转
WHOLE_CUBE = {
    "x": TURNS["R"],
    "y": TURNS["U"],
    "z": TURNS["F"],
}

# 整体转动逆时针复用
WHOLE_CUBE_INVERSE = {
    "x": INVERSE_TURNS["R"],
    "y": INVERSE_TURNS["U"],
    "z": INVERSE_TURNS["F"],
}


def rotate_point(turn_func, p: Coord) -> Coord:
    """对坐标点应用旋转公式。"""
    x, y, z = p
    return turn_func(x, y, z)
