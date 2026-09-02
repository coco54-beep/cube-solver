"""Cubie 与 BaseCube：魔方逻辑状态与转动引擎。

Cubie 数据:
    home:     已还原状态时的 3D 坐标 (tuple[int,int,int])
    pos:      当前 3D 坐标 (tuple[int,int,int])
    stickers: dict[方向向量(tuple) -> 颜色(str)]
              方向向量是该面 sticker 的法线方向 (单位向量)

转动逻辑 (apply_move):
    x/y/z 整体转动: 对所有 cubie 施加 WHOLE_CUBE 旋转。
    面转动: 按 FACE_AXIS_SIGN 选层 (pos[n_axis] in layer_values)，
            对选中 cubie 的 pos 与每个 sticker 方向向量施加 TURNS 旋转。
    180/270 度: 循环 count 次 (每次90度顺时针)。
"""

import copy
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from cube.coordinates import (
    FACE_AXIS_SIGN,
    FACE_NORMALS,
    TURNS,
    WHOLE_CUBE,
    is_in_layer,
)
from cube.notation import parse_move_str

Coord = Tuple[int, int, int]


@dataclass
class Cubie:
    home: Coord
    pos: Coord
    stickers: Dict[Tuple, str]

    @property
    def piece_type(self) -> str:
        """按 sticker 数量判定: 3=角, 2=棱, 1=中心。"""
        k = len(self.stickers)
        if k == 3:
            return "corner"
        if k == 2:
            return "edge"
        if k == 1:
            return "center"
        return "unknown"

    def clone(self):
        return Cubie(
            home=self.home,
            pos=self.pos,
            stickers=dict(self.stickers),
        )


def build_solved_cube(n: int, colors: Dict[str, str]) -> Dict[Coord, Cubie]:
    """构建已还原魔方。

    遍历所有 3D 坐标，对每个坐标检查 6 个面方向：
    若 pos[axis] == sign*maxc，则贴该面中心颜色。
    无 sticker 的内部块不建 cubie。

    返回 dict: pos -> Cubie (已还原时 home == pos)。
    """
    from cube.coordinates import coord_values, get_d_maxc

    d, maxc = get_d_maxc(n)
    vals = coord_values(n)

    # 面方向检测: (axis, sign, face)
    face_dirs = []
    for face, (n_axis, n_sign) in FACE_AXIS_SIGN.items():
        normal = FACE_NORMALS[face]
        face_dirs.append((n_axis, n_sign, normal, face))

    cubies: Dict[Coord, Cubie] = {}
    for x in vals:
        for y in vals:
            for z in vals:
                pos = (x, y, z)
                stickers: Dict[Tuple, str] = {}
                for axis, sign, normal, face in face_dirs:
                    if pos[axis] == sign * maxc:
                        stickers[normal] = colors[face]
                if stickers:
                    cubies[pos] = Cubie(home=pos, pos=pos, stickers=stickers)
    return cubies


class BaseCube:
    """魔方逻辑状态基类。"""

    size: int = 3

    def __init__(self, cubies: Dict[Coord, Cubie]):
        self.cubies = cubies  # 以当前 pos 为键
        self.n = self.size

    # -- 状态查询 --
    def cubie_at(self, pos: Coord):
        return self.cubies.get(pos)

    def is_solved(self) -> bool:
        """每面方向 sticker 颜色数量 == n*n 且同色。"""
        from cube.coordinates import coord_values, get_d_maxc

        d, maxc = get_d_maxc(self.n)
        face_dirs = []
        for face, (axis, sign) in FACE_AXIS_SIGN.items():
            normal = FACE_NORMALS[face]
            face_dirs.append((face, axis, sign, normal))

        for face, axis, sign, normal in face_dirs:
            colors_on_face = set()
            count = 0
            for cubie in self.cubies.values():
                if cubie.pos[axis] == sign * maxc:
                    col = cubie.stickers.get(normal)
                    if col is not None:
                        colors_on_face.add(col)
                        count += 1
            # 每面应有 n*n 个 sticker，且只有一种颜色
            if count != self.n * self.n or len(colors_on_face) != 1:
                return False
        return True

    def clone(self):
        return type(self)(copy.deepcopy(self.cubies))

    # -- 转动引擎 --
    def apply_move(self, move_str: str) -> None:
        """应用单个动作（字符串），就地更新状态。"""
        label, is_wide, count = parse_move_str(move_str)
        for _ in range(count):
            self._apply_single_quarter(label, is_wide)

    def apply_moves(self, moves: List[str]) -> None:
        for m in moves:
            self.apply_move(m)

    def _apply_single_quarter(self, label: str, is_wide: bool) -> None:
        """应用一个顺时针90度转动。"""
        if label in ("x", "y", "z"):
            rot = WHOLE_CUBE[label]
            self._rotate_all(rot)
            return

        n_axis, n_sign = FACE_AXIS_SIGN[label]
        rot = TURNS[label]
        selected = [c for c in self.cubies.values()
                    if is_in_layer(self.n, label, is_wide, c.pos)]
        new_cubies: Dict[Coord, Cubie] = {}
        for c in self.cubies.values():
            if c in selected:
                c = c.clone()
                c.pos = rot(*c.pos)
                c.stickers = {rot(*d): col for d, col in c.stickers.items()}
            new_cubies[c.pos] = c
        self.cubies = new_cubies

    def _rotate_all(self, rot) -> None:
        """整体转动：所有 cubie 的 pos 与 sticker 方向同时旋转。"""
        new_cubies: Dict[Coord, Cubie] = {}
        for c in self.cubies.values():
            c = c.clone()
            c.pos = rot(*c.pos)
            c.stickers = {rot(*d): col for d, col in c.stickers.items()}
            new_cubies[c.pos] = c
        self.cubies = new_cubies
