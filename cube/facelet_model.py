"""Facelet 前端模型：以 cubies 为权威状态，facelets 按需导出。

适用 UI / 校验 / 打乱展示。3x3 与 4x4 共用同一套转换与校验逻辑。
"""

import copy
from typing import Dict, List

from cube.conversion import facelets_to_cubies
from cube.cubie_model import BaseCube
from cube.validation import validate_2x2, validate_3x3, validate_4x4


class FaceletCube:
    def __init__(self, facelets: Dict[str, List[List[str]]], n: int):
        self.n = n
        self._base = BaseCube(facelets_to_cubies(facelets, n))
        self._base.n = n

    # -- 状态查询 --
    @property
    def facelets(self) -> Dict[str, List[List[str]]]:
        from cube.conversion import cubies_to_facelets
        return cubies_to_facelets(self._base.cubies, self.n)

    def is_solved(self) -> bool:
        return self._base.is_solved()

    # -- 转动 --
    def apply_move(self, move: str) -> None:
        self._base.apply_move(move)

    def apply_moves(self, moves: List[str]) -> None:
        self._base.apply_moves(moves)

    # -- 校验 --
    def validate(self) -> List[str]:
        if self.n == 2:
            return validate_2x2(self.facelets)
        if self.n == 3:
            return validate_3x3(self.facelets)
        return validate_4x4(self.facelets)

    # -- 复制 --
    def clone(self) -> "FaceletCube":
        base = self._base.clone()
        base.n = self.n
        fc = FaceletCube.__new__(FaceletCube)
        fc.n = self.n
        fc._base = base
        return fc
