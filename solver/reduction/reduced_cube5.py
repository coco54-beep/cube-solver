"""5x5 降阶映射：把「中心按颜色归面 + 12 条逻辑棱全部配对」的 Cube5 映射为
等效 3x3 facelet（供 solver3 / hkociemba 求解）。

映射规则（参照 4x4 版，但对 maxc=6 与 3 块棱做适配）：
- 中心：中心已按颜色归面，取每个物理面任一单贴面块的实际颜色作为该面颜色
  （固定面心/活动中心同色，取任一，支持任意配色/换面中心色）。
- 角块：8 个实体角块（坐标 ±6 三组合）对应 3x3 的 8 个角位。
- 棱块：每个 5x5 逻辑棱槽（1 中 + 2 翼，共 3 块）折叠为一个 3x3 棱位；
  配对完成后三块同色同朝向，任取一块贴向该面的 sticker 颜色即可。

纯几何映射，不做求解/校验。调用前置条件由调用方保证：
    centers_are_color_solved(cube) and all_edges_paired(cube)。
"""

from typing import Dict, List, Tuple

from cube.coordinates import FACE_AXIS_SIGN, FACE_NORMALS, FACE_SPEC, coord_values, get_d_maxc
from cube.cube5 import Cube5
from solver.edge5.positions import COORD_TO_SLOT, SLOT_NAMES, slot

Coord = tuple

# 5x5 逻辑棱槽名 -> 3x3 棱位（坐标按 3x3 离散值 {-1,0,1}），与 4x4 版一致
SLOT3 = {
    "FU": (0, 1, 1), "RU": (1, 1, 0), "BU": (0, 1, -1), "LU": (-1, 1, 0),
    "FD": (0, -1, 1), "RD": (1, -1, 0), "BD": (0, -1, -1), "LD": (-1, -1, 0),
    "FR": (1, 0, 1), "BR": (1, 0, -1), "FL": (-1, 0, 1), "BL": (-1, 0, -1),
}

# 5x5 角位 -> 3x3 角位
CORNER3 = {
    (6, 6, 6): (1, 1, 1), (6, 6, -6): (1, 1, -1),
    (-6, 6, 6): (-1, 1, 1), (-6, 6, -6): (-1, 1, -1),
    (6, -6, 6): (1, -1, 1), (6, -6, -6): (1, -1, -1),
    (-6, -6, 6): (-1, -1, 1), (-6, -6, -6): (-1, -1, -1),
}

_FACE_BY_AXIS = {0: ("R", "L"), 1: ("U", "D"), 2: ("F", "B")}

_MAXC = 6


def _sign(nv):
    for v in nv:
        if abs(v) == 1:
            return 1 if v > 0 else -1
    return 1


def _axis(nv):
    for i, v in enumerate(nv):
        if abs(v) == 1:
            return i
    return 0


def _rc(face: str, pos: Coord):
    """3x3 棱/角位 pos 在该面上的 (row, col)。"""
    n_axis, n_sign, row_axis, row_sign, col_axis, col_sign = FACE_SPEC[face]
    vals = coord_values(3)
    r = vals.index(pos[row_axis] * row_sign)
    c = vals.index(pos[col_axis] * col_sign)
    return r, c


def _is_corner_pos(pos: Coord) -> bool:
    return sorted(abs(v) for v in pos) == [_MAXC, _MAXC, _MAXC]


def _face_center_color(cube: Cube5, face: str) -> str:
    """取某个物理面的任一单贴面块颜色。固定面心 / 活动中心同色。"""
    n = FACE_NORMALS[face]
    ax, sg = FACE_AXIS_SIGN[face]
    for pos, cub in cube.cubies.items():
        if len(cub.stickers) == 1 and pos[ax] == sg * _MAXC:
            col = cub.stickers.get(n)
            if col is not None:
                return col
    raise ValueError("面 %s 缺少单贴面块" % face)


def _slot_of(pos: Coord) -> tuple:
    """5x5 棱坐标 -> 逻辑槽名。"""
    return COORD_TO_SLOT[pos]


def build_reduced_facelets(cube: Cube5) -> Dict[str, List[List[str]]]:
    """把配好棱的 5x5 映射为 3x3 facelets 字典。纯几何映射，不做校验。"""
    faces = {f: [["" for _ in range(3)] for _ in range(3)] for f in "URFDLB"}
    # 中心
    for f in "URFDLB":
        faces[f][1][1] = _face_center_color(cube, f)
    # 角块
    for p5, p3 in CORNER3.items():
        cub = cube.cubies.get(p5)
        if cub is None:
            continue
        for f, n in FACE_NORMALS.items():
            col = cub.stickers.get(n)
            if col is not None:
                r, c = _rc(f, p3)
                faces[f][r][c] = col
    # 棱块：每个逻辑槽任取一块（中/翼），取其朝该面的 sticker 颜色
    for name in SLOT_NAMES:
        p3 = SLOT3.get(name)
        if p3 is None:
            # 槽名顺序不同（UF vs FU），做翻转映射
            p3 = SLOT3.get(name[1] + name[0])
            if p3 is None:
                continue
        s = slot(name)
        # 任取 3 块中的一块（优先中棱）
        for p in (s.middle, s.left_wing, s.right_wing):
            cub = cube.cubies.get(p)
            if cub is None or len(cub.stickers) != 2:
                continue
            for f in name:
                n = FACE_NORMALS[f]
                col = cub.stickers.get(n)
                if col is not None:
                    r, c = _rc(f, p3)
                    faces[f][r][c] = col
            break
    return faces


def reduced_cubestring(cube: Cube5) -> str:
    """直接返回 3x3 的 54 字符合成串（供 solver3 / hkociemba 使用）。"""
    from solver.solver3 import _build_cubestring
    return _build_cubestring(build_reduced_facelets(cube))


def reduced_facelets_from_cubies(cubies) -> Dict[str, List[List[str]]]:
    """兼容便捷入口：接收 cubies 字典（非 Cube 实例）。"""
    cube = Cube5(cubies)
    return build_reduced_facelets(cube)
