"""2x2 魔方状态模型（仅含角块）。

2 阶魔方没有棱块与中心块，只有 8 个角块；转动为纯面转动（无宽层）。
模型仍复用通用 BaseCube / build_solved_cube，仅需 n=2 坐标系。
"""

from typing import Dict, Optional

from cube.cubie_model import BaseCube, build_solved_cube
from cube.colors import DEFAULT_COLORS


class Cube2(BaseCube):
    size = 2

    @classmethod
    def solved(cls, colors: Optional[Dict[str, str]] = None) -> "Cube2":
        if colors is None:
            colors = DEFAULT_COLORS
        return cls(build_solved_cube(2, colors))
