"""5x5 魔方状态模型。"""

from typing import Dict, Optional

from cube.cubie_model import BaseCube, build_solved_cube
from cube.colors import DEFAULT_COLORS


class Cube5(BaseCube):
    size = 5

    @classmethod
    def solved(cls, colors: Optional[Dict[str, str]] = None) -> "Cube5":
        if colors is None:
            colors = DEFAULT_COLORS
        return cls(build_solved_cube(5, colors))
