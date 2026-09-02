"""3D魔方智能还原助手 - 核心魔方模型包。

本包提供与UI无关的魔方逻辑状态模型：
- colors: 颜色常量
- coordinates: 统一坐标系、面网格映射、转动旋转公式
- notation: 公式解析/标准化/逆公式
- cubie_model: Cubie 与 BaseCube（转动引擎）
- conversion: facelet <-> cubie 互转
- facelet_model: 录入用 FaceletModel
- cube3 / cube4: 3阶/4阶具体实现
- validation: 合法性校验
"""

from cube.colors import DEFAULT_COLORS, VALID_COLORS, COLOR_NAMES
from cube.cubie_model import Cubie, BaseCube, build_solved_cube
from cube.notation import (
    parse_algorithm,
    parse_move_str,
    normalize_move,
    inverse_move,
    inverse_algorithm,
)

__all__ = [
    "DEFAULT_COLORS",
    "VALID_COLORS",
    "COLOR_NAMES",
    "Cubie",
    "BaseCube",
    "build_solved_cube",
    "parse_algorithm",
    "parse_move_str",
    "normalize_move",
    "inverse_move",
    "inverse_algorithm",
]
