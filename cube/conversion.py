"""Facelet <-> Cubie 双向转换。

facelets 结构:
    Dict[face, grid]  其中 grid[r][c] 为颜色字符串。
    r, c 从 0 开始，尺寸 n x n。

cubies 结构:
    Dict[pos, Cubie]  见 cube.cubie_model。

home 约定:
    facelet 输入不含"原 home 块"信息，转换后每个 cubie 的 home = pos
    （即校验按颜色/块结构进行，而非按 home 位移）。
"""

from typing import Dict, List

from cube.coordinates import (
    FACE_NORMALS,
    pos_from_rc,
)
from cube.cubie_model import Cubie

Coord = tuple


def facelets_to_cubies(
    facelets: Dict[str, List[List[str]]],
    n: int,
) -> Dict[Coord, Cubie]:
    """facelets -> cubies。按 3D 坐标聚合 sticker，home = pos。"""
    cubies: Dict[Coord, Cubie] = {}
    for face, grid in facelets.items():
        normal = FACE_NORMALS[face]
        for r in range(n):
            for c in range(n):
                pos = pos_from_rc(n, face, r, c)
                color = grid[r][c]
                cub = cubies.get(pos)
                if cub is None:
                    cub = Cubie(home=pos, pos=pos, stickers={})
                    cubies[pos] = cub
                cub.stickers[normal] = color
    return cubies


def cubies_to_facelets(
    cubies: Dict[Coord, Cubie],
    n: int,
) -> Dict[str, List[List[str]]]:
    """cubies -> facelets。逐面逐格取朝向法线的 sticker。"""
    faces = list(FACE_NORMALS.keys())
    facelets: Dict[str, List[List[str]]] = {f: [] for f in faces}
    for face in faces:
        normal = FACE_NORMALS[face]
        for r in range(n):
            row: List[str] = []
            for c in range(n):
                pos = pos_from_rc(n, face, r, c)
                cub = cubies.get(pos)
                color = cub.stickers.get(normal) if cub is not None else None
                row.append(color)
            facelets[face].append(row)
    return facelets
