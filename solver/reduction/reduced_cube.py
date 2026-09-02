"""4x4 降阶映射：把中心还原且棱块配对的 4x4 映射为等效 3x3 facelet。

映射规则：
- 中心：已还原，直接使用默认面配色。
- 角块：4x4 的 8 个角块（坐标 ±3）对应 3x3 的 8 个角位。
- 棱块：每个 4x4 棱槽（两个翼位）折叠为一个 3x3 棱位。取翼块朝向该面
  的 sticker 颜色作为 3x3 棱块的该面颜色（配对完成后两个翼块同色，任取
  一个即可）。

此模块不求解、不校验，只做纯几何映射。
"""

from typing import Dict, List

from cube.conversion import cubies_to_facelets
from cube.coordinates import FACE_NORMALS, FACE_SPEC, coord_values
from cube.cube4 import Cube4

Coord = tuple

# 4x4 棱槽名 -> 3x3 棱位（坐标按 3x3 离散值 {-1,0,1}）
SLOT3 = {
    "FU": (0, 1, 1), "RU": (1, 1, 0), "BU": (0, 1, -1), "LU": (-1, 1, 0),
    "FD": (0, -1, 1), "RD": (1, -1, 0), "BD": (0, -1, -1), "LD": (-1, -1, 0),
    "FR": (1, 0, 1), "BR": (1, 0, -1), "FL": (-1, 0, 1), "BL": (-1, 0, -1),
}

# 4x4 角位 -> 3x3 角位
CORNER3 = {
    (3, 3, 3): (1, 1, 1), (3, 3, -3): (1, 1, -1),
    (-3, 3, 3): (-1, 1, 1), (-3, 3, -3): (-1, 1, -1),
    (3, -3, 3): (1, -1, 1), (3, -3, -3): (1, -1, -1),
    (-3, -3, 3): (-1, -1, 1), (-3, -3, -3): (-1, -1, -1),
}

_FACE_BY_AXIS = {0: ("R", "L"), 1: ("U", "D"), 2: ("F", "B")}


def _axis(nv):
    for i, v in enumerate(nv):
        if abs(v) == 1:
            return i
    return 0


def _sign(nv):
    for v in nv:
        if abs(v) == 1:
            return 1 if v > 0 else -1
    return 1


def _slot_of(pos: Coord) -> tuple:
    fs = []
    for ax, v in enumerate(pos):
        if abs(v) == 3:
            fs.append(_FACE_BY_AXIS[ax][0] if v > 0 else _FACE_BY_AXIS[ax][1])
    return tuple(sorted(fs))


def _rc(face: str, pos: Coord):
    """3x3 棱/角位 pos 在该面上的 (row, col)。"""
    n_axis, n_sign, row_axis, row_sign, col_axis, col_sign = FACE_SPEC[face]
    vals = coord_values(3)
    r = vals.index(pos[row_axis] * row_sign)
    c = vals.index(pos[col_axis] * col_sign)
    return r, c


def build_reduced_facelets(cube) -> Dict[str, List[List[str]]]:
    """把 4x4 cubies 映射为 3x3 facelets 字典。

    要求 cube 中心已还原、12 个棱组已配对。纯几何映射，不做校验。
    """
    faces = {f: [["" for _ in range(3)] for _ in range(3)] for f in "URFDLB"}
    # 中心：取 4x4 该物理面任一中心块（单色）的实际颜色，
    # 支持中心色整体换面/随机配色。
    from cube.coordinates import get_d_maxc
    _, maxc = get_d_maxc(cube.n)
    for f, n in FACE_NORMALS.items():
        for pos, cub in cube.cubies.items():
            if len(cub.stickers) == 1 and pos[_axis(n)] == _sign(n) * maxc:
                col = cub.stickers.get(n)
                if col is not None:
                    faces[f][1][1] = col
                break
    # 角块
    for p4, p3 in CORNER3.items():
        cub = cube.cubies.get(p4)
        if cub is None:
            continue
        for f, n in FACE_NORMALS.items():
            col = cub.stickers.get(n)
            if col is not None:
                r, c = _rc(f, p3)
                faces[f][r][c] = col
    # 棱块：每个槽任取一个翼块，取其朝该面的 sticker 颜色
    for name, p3 in SLOT3.items():
        poss = [p for p, c in cube.cubies.items()
                if len(c.stickers) == 2 and _slot_of(p) == tuple(sorted(name))]
        if len(poss) != 2:
            continue
        wing = cube.cubies[poss[0]]
        for f in name:
            n = FACE_NORMALS[f]
            col = wing.stickers.get(n)
            if col is not None:
                r, c = _rc(f, p3)
                faces[f][r][c] = col
    return faces


def reduced_cubestring(cube) -> str:
    """直接返回 3x3 的 54 字符合成串（供 solver3 / hkociemba 使用）。

    该路径跳过 cubies_to_facelets，避免 4x4 面贴到 3x3 面贴的中间表示。
    """
    facelets = build_reduced_facelets(cube)
    return _flatten(facelets)


def _flatten(facelets) -> str:
    """按 hkociemba 读取顺序 (U,R,F,D,L,B) 展平为 54 字符。"""
    from solver.solver3 import _build_cubestring
    return _build_cubestring(facelets)


def reduced_facelets_from_cubies(cubies) -> Dict[str, List[List[str]]]:
    """兼容便捷入口：接收 cubies 字典（非 Cube 实例）。"""
    cube = Cube4(cubies)
    return build_reduced_facelets(cube)
