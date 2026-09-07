"""物理中央切片（fixed-center-preserving）动作与记号映射。

**背景**：旧 `3X` 把切层当作_刚性几何平面_旋转，会把 4 个固定面心一并搬走 —— 那是
非物理实现。真实奇阶魔方执行中央切片时，中央切片内的可动棱块/活动中心会移动，而
**六个固定面心不交换位置**。

本模块提供：
- `apply_physical_token` / `apply_physical_sequence`：就地应用单个/整条动作，识别
  `M`/`E`/`S`（中央切片）与常规面/宽/整机转动，并 `3Rw`-类宽三转分解为 `2Rw + 切片`。
- `SLICE_TOKENS`：`M`→x 轴、`E`→y 轴、`S`→z 轴。
- `wide3_tokens` / `wide3_decompose`：`3Rw` = `2Rw` + 物理切片（方向与组合顺序在
  `tests/test_middle_slice.py` 中以置换验证，非字符串猜测）。

该功能**不介入**被冻结的中心求解器与普通 36 动作配棱搜索。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .coordinates import FACE_AXIS_SIGN

# 中央切片记号 -> 旋转轴（字母轴）。
SLICE_TOKENS = {"M": "x", "E": "y", "S": "z"}

# 每个轴对应的「移动的固定面心对」同向面转动标签（用于 wide3 分解的方向参考）。
_AXIS_FACE = {"x": "R", "y": "U", "z": "F"}


def slice_turns(token: str) -> Tuple[str, int]:
    """解析 `M`/`M'`/`M2` -> (axis, turns)。非法返回 None 的调用者自行处理。"""
    base = token[0]
    rest = token[1:]
    if base not in SLICE_TOKENS:
        return ("", 0)
    turns = {"": 1, "'": 3, "2": 2}.get(rest, 0)
    return SLICE_TOKENS[base], turns


def is_slice_token(token: str) -> bool:
    return token[0] in SLICE_TOKENS if token else False


def apply_physical_token(cube, token: str) -> bool:
    """应用单个 token；成功返回 True，不认识返回 False。"""
    if token[0] in SLICE_TOKENS:
        axis, turns = slice_turns(token)
        if turns == 0:
            raise ValueError(f"非法切片后缀: {token!r}")
        cube.apply_inner_slice(axis, turns)
        return True
    # 会搬走固定面心的宽3及以上（非物理 `3X`）拒绝；其余单层/宽二层/整机转动放行。
    if is_fixed_center_moving(token):
        raise ValueError(f"固定面心移动动作（非物理宽3/中slice机制）: {token!r}")
    cube.apply_move(token)
    return True


def apply_physical_sequence(cube, tokens: List[str]) -> None:
    for tk in tokens:
        apply_physical_token(cube, tk)


def is_fixed_center_moving(token: str) -> bool:
    """是否 `3X`-类（宽三层或以上）会以刚性平面搬走固定面心。"""
    digits = ""
    for ch in token:
        if ch.isdigit():
            digits += ch
        else:
            break
    return bool(digits) and int(digits) >= 3


def wide3_decompose(face: str, turns: int = 1) -> List[str]:
    """`3Rw`（宽三转）物理分解 = `2Rw`（宽二）+ 中央切片。

    方向与组合顺序由测试按置换验证（`tests/test_middle_slice.py`）。
    face 为单层面标签（R/U/F…）；turns 1/2/3 = 90/180/270。
    """
    axis = {v: k for k, v in _AXIS_FACE.items()}[face]
    suffix = "" if turns == 1 else ("2" if turns == 2 else "'")
    wide2 = "2" + face + suffix
    slice_tok = _slice_token_for_axis(axis, turns)
    return [wide2, slice_tok]


def _slice_token_for_axis(axis: str, turns: int) -> str:
    # 宽三层后补同方向切片 → 组合后保持固定面心。方向与组合顺序在测试中验证。
    inv_face = {"x": "L", "y": "D", "z": "B"}[axis]
    suffix = "" if turns == 1 else ("2" if turns == 2 else "'")
    # 切片方向与 2Rw 同向：绕轴旋转，方向由 `_AXIS_FACE`/`_slice_turns` 决定，
    # 具体取 M/M'/M2 由置换测试 `test_3rw_matches_2rw_plus_physical_middle_slice` 校准。
    letter = {"x": "M", "y": "E", "z": "S"}[axis]
    return letter + suffix
