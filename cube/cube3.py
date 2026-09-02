"""3x3 魔方状态模型。"""

from typing import Dict, Optional

from cube.cubie_model import BaseCube, build_solved_cube
from cube.colors import DEFAULT_COLORS


class Cube3(BaseCube):
    size = 3

    @classmethod
    def solved(cls, colors: Optional[Dict[str, str]] = None) -> "Cube3":
        if colors is None:
            colors = DEFAULT_COLORS
        return cls(build_solved_cube(3, colors))
