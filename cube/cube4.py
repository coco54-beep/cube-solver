"""4x4 魔方状态模型（含宽层转动）。"""

from typing import Dict, Optional

from cube.cubie_model import BaseCube, build_solved_cube
from cube.colors import DEFAULT_COLORS


class Cube4(BaseCube):
    size = 4

    @classmethod
    def solved(cls, colors: Optional[Dict[str, str]] = None) -> "Cube4":
        if colors is None:
            colors = DEFAULT_COLORS
        return cls(build_solved_cube(4, colors))
