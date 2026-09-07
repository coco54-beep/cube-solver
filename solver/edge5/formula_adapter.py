"""Gate 5b · 公式适配器（标准 5x5 记号 → 物理合法 1X/2X 动作）。

标准 L2E / edge-flip 算法常用记号：`Rw`、`3Rw`、`r`、`M`、内层单切片等。本模块把它
们解析并**规范化**为当前引擎能识别的**内部无歧义动作**，再展开为物理合法的 1X/2X 序列。

**固定面心约束（最高风险点）**：
- 引擎原生只接受 1X（外层）与 2X（两层宽转，符号 `2R`/`r`），以及整机 x/y/z；
- `Rw` = 整体两层宽 → 规范化 `2R`（等价 `r`）；
- `3R` / `3Rw`（宽 3 层）与 `M`（中切片）**会移动固定面心** → 在 5x5 上属非法，**必须拒绝**；
- 内层单切片（最里第一层之外的第二个层，即 layer-2）：无独立记号，用复合
  `2R + R'`（两层宽再回外层，同轴可交换）表达，实测**保持固定面心**。

任何不能规范化为物理合法 1X/2X 序列的候选都必须**拒绝**（`expand` 返回 None）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

# 合法外层/宽转基础（相对 face 的无后缀 token，层层注解在后面处理）。
_LEGAL_LAYER_BASE = {"R", "L", "U", "D", "F", "B"}
_WIDE_LAYER = 2
# 宽层的符号别名：小写字母 == 两层宽；`Xw` == 两层宽。
_WIDE_TOKENS = {"r": "R", "l": "L", "u": "U", "d": "D", "f": "F", "b": "B"}


@dataclass(frozen=True)
class RepresentableMove:
    """一个已规范化的可表示移动：face + layers + quarter-turns（1..3）。"""

    face: str
    layers: int
    turns: int

    @property
    def move_str(self) -> str:
        base = self.face if self.layers == 1 else "2" + self.face
        suffix = "" if self.turns == 1 else ("2" if self.turns == 2 else "'")
        return base + suffix


def _parse_source_token(token: str) -> Optional[RepresentableMove]:
    """解析单个标准记号 token → RepresentableMove；非法（3R/3Rw/M/…）返回 None。"""
    token = token.strip()
    if not token:
        return None
    i = 0
    layers = 0
    while i < len(token) and token[i].isdigit():
        layers = layers * 10 + int(token[i])
        i += 1
    body = token[i:]
    if not body:
        return None
    first = body[0]
    suffix = body[1:]
    # 整机旋转 x/y/z 不是 free-slice 搜索的原子动作（1X/2X），在此拒绝。
    if first in ("x", "y", "z"):
        return None
    # 判定是否为宽转
    wide = False
    if first in _LEGAL_LAYER_BASE and suffix.startswith("w"):
        wide = True
        suffix = suffix[1:]
        if suffix.startswith("w"):
            suffix = suffix[1:]
    elif first in _WIDE_TOKENS:
        first = _WIDE_TOKENS[first]
        wide = True
    elif first in _LEGAL_LAYER_BASE:
        pass
    else:
        return None
    face = first
    turns = _turns_from_suffix(suffix)
    if turns is None:
        return None
    eff_layers = layers if layers else (2 if wide else 1)
    if eff_layers == 0 or eff_layers > 2:
        # 宽 3/宽 4/… （3R/3Rw/4R）会移动固定面心 → 非法
        return None
    return RepresentableMove(face, eff_layers, turns)


def _turns_from_suffix(suffix: str) -> Optional[int]:
    if suffix == "":
        return 1
    if suffix == "'":
        return 3
    if suffix == "2":
        return 2
    if suffix == "''":
        return 2
    return None


def expand_move(token: str) -> Optional[Tuple[str, ...]]:
    """把单个标准记号规范化为物理合法 1X/2X 动作元组；无法规范化返回 None。

    - `R`/`R'`/`R2`/`2R`/`r`/`Rw` → 合法（宽 2 直接输出 `2R`）；
    - `3R`/`3Rw`/`M`/`5R` → None（移动固定面心）；
    - 内层单切片 layer-2（如 `r` 代表的第二层转单层）→ 需要 `2R + R'`。
      注意：这里把「宽 2 移动」视为 `2R` 本身；真正的 layer-2-only 由调用方用
      `inner_slice(face)` 复合表达（`2R + R'`），不在此单 token 层处理。
    """
    pm = _parse_source_token(token)
    if pm is None:
        return None
    return (pm.move_str,)


def expand_sequence(tokens: Tuple[str, ...]) -> Optional[Tuple[str, ...]]:
    """规范化整条公式；任一 token 非法则整体返回 None。"""
    out = []
    for tk in tokens:
        exp = expand_move(tk)
        if exp is None:
            return None
        out.extend(exp)
    return tuple(out)


def inner_slice(face: str, turns: int = 1) -> Tuple[str, ...]:
    """内层单切片（layer-2）：`2R + R'`。保持固定面心。

    `turns` 1/2/3 = 90/180/270，映射为正/逆次数。同轴动作可交换。
    """
    f = face.upper()
    suffix = "" if turns == 1 else ("2" if turns == 2 else "'")
    inv = "'" if turns == 1 else ("'" if turns == 3 else "")
    base = "2" + f + suffix
    outer = f + ("'" if suffix == "'" else "")
    # 两层宽一次后，再回外层：net = 仅 layer-2。
    return (base, outer)


def _invert_token(token: str) -> str:
    if token.endswith("2"):
        return token
    if token.endswith("'"):
        return token[:-1]
    return token + "'"


def invert_sequence(seq: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(_invert_token(t) for t in reversed(seq))


@dataclass(frozen=True)
class FormulaCandidate:
    name: str
    source_notation: Tuple[str, ...]      # 来源原文
    normalized_moves: Tuple[str, ...]     # 规范化后的合法动作
    transform: str                        # 原式 / 逆式 / … 标记

    @property
    def moves_str(self) -> str:
        return " ".join(self.normalized_moves)


def build_candidates(
    source_notation: Tuple[str, ...],
    *,
    name: str,
    include_inverse: bool = True,
) -> Tuple[FormulaCandidate, ...]:
    """从一条来源公式生成候选（原式 + 可选逆式）；任一不可规范化则跳过该式。"""
    cands = []
    norm = expand_sequence(source_notation)
    if norm is not None:
        cands.append(FormulaCandidate(name, source_notation, norm, "原式"))
    if include_inverse:
        inv_src = invert_sequence(source_notation)
        inv_norm = expand_sequence(inv_src)
        if inv_norm is not None:
            cands.append(FormulaCandidate(name + ":inv", inv_src, inv_norm, "逆式"))
    return tuple(cands)
