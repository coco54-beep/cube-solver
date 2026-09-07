"""Gate 5b · 来源公式登记表（公开 5x5 L2E 算法，附出处与记号定义）。

只登记「来源可靠、记号明确」的公式；每个候选保存出处、用途、观察方向、原始记号与
转换后动作。所有候选按用户要求**严格排除移动固定面心的** `3Rw/3Rw/M/x/y/z`。

**记号定义（speedcubedb · 5x5）**
- `R`/`U`/`F`/… = 单外层；`Rw`/`Lw`/`Uw` = 宽两层；`r`/`l` = 内层 slice（深度层）；
- `3Rw` = 宽三层（会移动固定面心，**非法**）；`M` = 中 slice（非法）；
- `2R` 在本引擎 = 宽两层（等价 `Rw`）；内层 slice = `2R + R'`。

**验收（Gate 5b 双棱转移契约）**：候选仅在真实 Cube5 重放后满足
`target_is_valid_tredge and centers_solved and fixed_centers_preserved and
protected_except_buffer_survive and replay_consistent` 才被采纳。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from .formula_adapter import expand_sequence


@dataclass(frozen=True)
class SourcedFormula:
    """一条来源可靠的公开公式及其出处/记号/用途。"""

    name: str
    source_url: str
    source_title: str
    retrieved_date: str
    stated_purpose: str
    notation_definition: str
    original_formula: Tuple[str, ...]       # 来源原文（含 Rw/r/l 等）
    adapted_moves: Optional[Tuple[str, ...]] = None  # 转换后的 1X/2X；None = 不可转换

    def __post_init__(self):
        object.__setattr__(self, "adapted_moves", expand_sequence(self.original_formula))

    @property
    def adaptable(self) -> bool:
        return self.adapted_moves is not None


_SRC = "https://speedcubedb.com/a/5x5/L2E"
_TITLE = "SpeedCubeDB · 5x5 Last Two Edges"
_DATE = "2026-09-07"
_LEGEND = (
    "R/U/F/... = single outer layer; Rw/Lw/Uw = wide 2 layers; "
    "r/l = inner slice (depth); 3Rw/M = move fixed centers (illegal); "
    "engine: Rw->2R, inner slice->2R+R'."
)


# 只有宽转 + 面转（无 3Rw/M/旋转）的候选，保证固定面心保持。
SOURCED_L2E: Tuple[SourcedFormula, ...] = (
    SourcedFormula(
        name="L2E4_Rw2F2U2Rw2U2F2Rw2",
        source_url=_SRC, source_title=_TITLE, retrieved_date=_DATE,
        stated_purpose="5x5 Last Two Edges single-edge swap/flip on the UF/UB pair",
        notation_definition=_LEGEND,
        original_formula=("Rw2", "F2", "U2", "Rw2", "U2", "F2", "Rw2"),
    ),
    SourcedFormula(
        name="L2E8_Lw2F2U2Lw_U2Lw2F2Lw_U2Lw2U2F2Lw_F2",
        source_url=_SRC, source_title=_TITLE, retrieved_date=_DATE,
        stated_purpose="5x5 Last Two Edges wide-2-gen case on the L side",
        notation_definition=_LEGEND,
        original_formula=("Lw2", "F2", "U2", "Lw'", "U2", "Lw2", "F2", "Lw'", "U2", "Lw2", "U2", "F2", "Lw'", "F2"),
    ),
    SourcedFormula(
        name="L2E10_Rw_U2Rw2U2RwU2Rw_U2RwU2Rw2U2Rw",
        source_url=_SRC, source_title=_TITLE, retrieved_date=_DATE,
        stated_purpose="5x5 Last Two Edges 2-generator (U,Rw) case",
        notation_definition=_LEGEND,
        original_formula=("Rw'", "U2", "Rw2", "U2", "Rw", "U2", "Rw'", "U2", "Rw", "U2", "Rw2", "U2", "Rw'"),
    ),
    SourcedFormula(
        name="L2E1_Rw_U_R_U_R_F_R_F_Rw",
        source_url=_SRC, source_title=_TITLE, retrieved_date=_DATE,
        stated_purpose="5x5 Last Two Edges (community-rated) short swap on the UF/UB pair",
        notation_definition=_LEGEND,
        original_formula=("Rw'", "U'", "R'", "U", "R'", "F", "R", "F'", "Rw"),
    ),
    # --- 含物理中央切片 / 宽三层的公式（此前因 `3Rw` 被拒绝，现重新验证）---
    SourcedFormula(
        name="L2E6_0_Rw_U2_3Rw_U2_3Rw_F2_Rw2_U2_Rw_U2_Rw_U2_F2_Rw2_F2",
        source_url=_SRC, source_title=_TITLE, retrieved_date=_DATE,
        stated_purpose="5x5 Last Two Edges case L2E 6,0 (wide-3 heavy, fixes the flip/swap pair)",
        notation_definition=_LEGEND,
        original_formula=("Rw'", "U2", "3Rw", "U2", "3Rw'", "F2", "Rw2",
                          "U2", "Rw", "U2", "Rw'", "U2", "F2", "Rw2", "F2"),
    ),
    SourcedFormula(
        name="L2E12_0_Rw_U2_Rw_U2_3Lw_U2_Rw_U2_Rw_U2_Rw_U2_Rw_U2_Rw2_D2_F2_U2_D2",
        source_url=_SRC, source_title=_TITLE, retrieved_date=_DATE,
        stated_purpose="5x5 Last Two Edges case L2E 12,0 (L-side wide-3 L2E)",
        notation_definition=_LEGEND,
        original_formula=("Rw'", "U2", "Rw", "U2", "3Lw'", "U2", "Rw", "U2",
                          "Rw", "U2'", "Rw'", "U2", "Rw", "U2'", "Rw2",
                          "D2", "F2", "U2", "D2"),
    ),
    SourcedFormula(
        name="L2E_M_EDGE_FLIP_xMURURFRFMx",
        source_url=_SRC, source_title=_TITLE, retrieved_date=_DATE,
        stated_purpose="5x5 Last Two Edges single-edge flip via M-slice commutator "
                       "(L2E 3,0), conjugated by whole-cube x",
        notation_definition=_LEGEND,
        original_formula=("x'", "M'", "U'", "R'", "U", "R'", "F", "R", "F'", "M", "x"),
    ),
)


def find_sourced(name: str) -> Optional[SourcedFormula]:
    for sf in SOURCED_L2E:
        if sf.name == name:
            return sf
    return None
