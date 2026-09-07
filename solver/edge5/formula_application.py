"""Gate 5b · Phase 2：来源公式的物理适配与效果分类。

标准 L2E / edge-flip 算法的来源记号（`R`/`Rw`/`r`/`M`/`E`/`S`/`3Rw`/`x y z`）在此被
**绑定来源的 notation legend**，逐一转换为无歧义的**内部物理动作**（全部属于：
外层 1X / 两层宽转 2X / 物理中央切片 `M E S`）。

**核心区分（用户裁定，covered by Phase 1）**：
- 旧 `3X` 把切层当**刚性几何平面**旋转，会搬走固定面心 —— 非物理，**禁用**。
- 标准 `3Rw` 本身合法 —— 在本引擎按 `2Rw + 物理M`（保持固定面心）分解。
- `M/E/S` 走 `cube.apply_inner_slice()`（物理中央切片）。

本模块**只做公式适配与效果分类**，不把候选接入正式 Gate 5b（那是 Phase 3 的事）。
每条候选输出 `FormulaOutcome` 而非只有 pass/fail，以便区分「布局错 / 方向错 / 类别不符」。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Sequence, Tuple

from cube.cube5 import Cube5
from cube.middle_slice import apply_physical_sequence

from .compact_state import state_of
from .free_slice import _fixed_centers_preserved, _slot_of_mid_idx, _slot_of_wing_idx
from .positions import SLOT_NAMES, slot
from .state import centers_are_color_solved, is_edge_paired

# 一条来源公式的「记号定义」：解释 `Rw/r/3Rw/M/E/S/x y z` 的含义。
class NotationLegend(Enum):
    SPEEDCUBEDB_5X5 = "speedcubedb_5x5"
    # 该 legend 下：
    #   R/U/F... = outer 1X
    #   Rw = wide 2X = 2R
    #   r  = 内层单切片（沿对应轴的第 2 层），对 5x5 是坐标绝对值 == 3 的那层
    #   M/E/S = 物理中央切片（坐标 == 0）
    #   3Rw = 2R + 物理中央切片（保持固定面心）
    #   x/y/z = 整体旋转：用于后续面名改写；无法改写则拒绝
    K4_SCALAR_5X5 = "k4_scalar_5x5"


_INNER_SLICE_LAYER_COORD = 3  # 5x5 上「第二层」单层的坐标绝对值（±3）


@dataclass(frozen=True)
class L2EPrecondition:
    """一条来源公式的真实前置槽位布局（不任意猜测）。"""

    target_slot: str                       # 目标 A 应处的槽
    buffer_slot: str                       # 缓冲 B 应处的槽
    target_signature: str                  # A 三块的期望签名（如 FLIPPED / GATHERED）
    buffer_signature: str                  # B 三块期望状态
    observation_frame: str                 # 观察方向（如 'UF' 面朝观察者）
    formula_name: str
    source_url: str


class FormulaOutcome(Enum):
    TARGET_VALID = "target_valid"                       # A 变 VALID（Gate 5b 成功）
    TARGET_STILL_FLIPPED = "target_still_flipped"       # A 仍翻转
    TARGET_SCATTERED = "target_scattered"               # A 三块被拆散
    TARGET_MOVED_GATHERED = "target_moved_gathered"     # A 被抓齐但仍是未配对/换位
    CENTER_BROKEN = "center_broken"                     # 中心未归面
    PROTECTED_BROKEN = "protected_broken"               # 非缓冲保护组被破坏
    NOTATION_UNSUPPORTED = "notation_unsupported"       # 记号无法物理化
    INVALID_STATE = "invalid_state"                     # 重放后状态非法（非双射等）


# ---------------------------------------------------------------------------
# 1. 记号 -> 内部物理动作
# ---------------------------------------------------------------------------

def _axis_of_slice_letter(letter: str) -> str:
    return {"M": "x", "E": "y", "S": "z"}[letter]


def _interpret_token(token: str, legend: NotationLegend) -> Optional[Tuple[str, ...]]:
    """把单个来源 token 解释为内部物理动作 token 元组。

    返回 None = 无法物理化（拒绝）。返回元组可为多个 token（如 `3Rw` -> `2R + M`）。
    """
    token = token.strip()
    if not token:
        return None
    # 前导数字（层数）。
    i = 0
    layers = 0
    while i < len(token) and token[i].isdigit():
        layers = layers * 10 + int(token[i])
        i += 1
    body = token[i:]
    if not body:
        return None
    first = body[0]
    rest = body[1:]
    # 剥离一个可能的 `w` 后缀标记。
    wide_marker = rest.startswith("w")
    if wide_marker:
        rest = rest[1:]
    # 处理 `''` 双撇号（=2）。
    if rest == "''":
        rest = "2"
    turns_map = {"": 1, "'": 3, "2": 2}
    if rest not in turns_map:
        return None
    turns = turns_map[rest]
    suffix = "" if turns == 1 else ("2" if turns == 2 else "'")

    upper = first.upper()
    face_letters = {"R", "L", "U", "D", "F", "B"}

    # x/y/z 整体旋转。
    if first in ("x", "y", "z"):
        # 整体旋转不能作为原子 free-slice 动作；这里返回 None，
        # 由上层尝试改写后续面名；若无法改写则整条拒绝。
        return None

    if first.islower() and upper in face_letters:
        # 小写 = 宽两层（speedcubedb 5x5 中 `r` 默认等价 `Rw` 宽两层）。
        # 注意：用户裁定「`r` 来源明确时映射为物理内切片」。
        # 对 K4 类 legend，`r` = 单内层切片；见下方按 legend 分支。
        face = upper
        if legend == NotationLegend.K4_SCALAR_5X5:
            # `r` = 内层单切片（坐标 |x|==3）→ 用 `2R + R'` 表达（同轴可交换）。
            inner = "2" + face + suffix
            outer = face + ("'" if turns == 1 else ("'" if turns == 3 else ""))
            return (inner, outer)
        # 默认 speedcubedb：`r` == `Rw` == 宽两层 `2R`。
        return ("2" + face + suffix,)

    if upper in face_letters:
        face = upper
        eff_layers = layers if layers else (2 if wide_marker else 1)
        if eff_layers >= 3:
            # `3Rw` / `3R`：宽三层，物理分解 = 宽两层 + 中央切片。
            # 仅当 wide 标记存在或层数由前导数字给出且 >=3 时才如此分解。
            inner_axis = {"R": "x", "L": "x", "U": "y", "D": "y",
                          "F": "z", "B": "z"}[face]
            slice_letter = _SLICE_BY_AXIS[inner_axis]
            return ("2" + face + suffix, slice_letter + suffix)
        return (("2" if eff_layers == 2 else "") + face + suffix,)

    if first in ("M", "E", "S"):
        # 物理中央切片：读取层数忽略（中央切片永远是一层），转次数按 suffix。
        return (first + suffix,)

    return None


_SLICE_BY_AXIS = {"x": "M", "y": "E", "z": "S"}


def parse_sourced_sequence(
    tokens: Sequence[str],
    legend: NotationLegend = NotationLegend.SPEEDCUBEDB_5X5,
) -> Optional[Tuple[str, ...]]:
    """把整条来源公式解析为内部物理动作序列；任一 token 无法物理化则整体返回 None。"""
    out: list = []
    for tk in tokens:
        interp = _interpret_token(tk, legend)
        if interp is None:
            return None
        out.extend(interp)
    return tuple(out)


def apply_sourced_sequence(cube: Cube5, seq: Tuple[str, ...]) -> None:
    """把一条内部物理动作序列重放到 cube 上（就地修改）。"""
    apply_physical_sequence(cube, list(seq))


# ---------------------------------------------------------------------------
# 2/4. 目标检索与效果分类
# ---------------------------------------------------------------------------

def find_gathered_tredge_slot(cube: Cube5, target_piece_ids: Tuple[int, int, int]) -> Optional[str]:
    """在全部 12 槽中搜索目标 A（中棱 + 两翼的 home 下标）是否被抓齐在**任一槽**。

    返回该槽名，若三块未聚集在任一槽返回 None。
    """
    mid_home, wa_home, wb_home = target_piece_ids
    st = state_of(cube)
    mid_slot = _slot_of_mid_idx(st, mid_home)
    wa_slot = _slot_of_wing_idx(st, wa_home)
    wb_slot = _slot_of_wing_idx(st, wb_home)
    if mid_slot is None or wa_slot is None or wb_slot is None:
        return None
    if mid_slot == wa_slot == wb_slot:
        return mid_slot
    return None


def target_is_orientation_valid(cube: Cube5, target_slot: str) -> bool:
    """目标 A 在 `target_slot` 是否已配对（`is_edge_paired`）。"""
    return is_edge_paired(cube, target_slot)


def non_buffer_protected_groups_survive(
    cube: Cube5,
    protected_slots: Sequence[str],
    *,
    protected_signature_before: Optional[Tuple[bool, ...]] = None,
) -> bool:
    """非缓冲保护组是否全部存活（每个 protected 槽在 after 仍保持「是否配对」不变）。

    若未提供 before 签名，则要求每个保护槽当前仍**已配对**（gate 起点默认保护组已配对）。
    """
    if protected_signature_before is None:
        return all(is_edge_paired(cube, s) for s in protected_slots)
    return all(
        is_edge_paired(cube, s) == sig
        for s, sig in zip(protected_slots, protected_signature_before)
    )


def classify_formula(
    cube: Cube5,
    *,
    target_piece_ids: Tuple[int, int, int],
    protected_slots: Sequence[str],
    protected_signature_before: Optional[Tuple[bool, ...]] = None,
) -> FormulaOutcome:
    """执行公式后的状态分类（A 是否变 VALID、中心、保护组）。"""
    slot_after = find_gathered_tredge_slot(cube, target_piece_ids)
    centers = centers_are_color_solved(cube)
    fixed = _fixed_centers_preserved(cube)
    protected_ok = non_buffer_protected_groups_survive(
        cube, protected_slots, protected_signature_before=protected_signature_before
    )
    if not centers or not fixed:
        return FormulaOutcome.CENTER_BROKEN
    if not protected_ok:
        return FormulaOutcome.PROTECTED_BROKEN
    if slot_after is None:
        # 三块未聚在任何槽 -> 被拆散
        return FormulaOutcome.TARGET_SCATTERED
    if target_is_orientation_valid(cube, slot_after):
        return FormulaOutcome.TARGET_VALID
    # 抓齐但未配对/仍翻转
    if slot_after is not None:
        return FormulaOutcome.TARGET_STILL_FLIPPED
    return FormulaOutcome.TARGET_MOVED_GATHERED


# ---------------------------------------------------------------------------
# 5. 公式变体生成
# ---------------------------------------------------------------------------

def _invert_token(tok: str) -> str:
    if tok.endswith("2"):
        return tok
    if tok.endswith("'"):
        return tok[:-1]
    return tok + "'"


def invert_internal(seq: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(_invert_token(t) for t in reversed(seq))


def _mirror_face(face: str) -> str:
    return {"R": "L", "L": "R", "U": "D", "D": "U", "F": "B", "B": "F"}.get(face, face)


def _mirror_token(tok: str) -> str:
    # 切层/整机：M<->M?（沿镜像轴反转方向），宽转字母面镜像。
    if tok[0] in ("M", "E", "S"):
        # 镜像对应面轴：M(x)->M 方向反转；E(y)->E 反转；S(z)->S 反转。
        return _invert_token(tok) if tok not in ("M2", "E2", "S2") else tok
    digits = ""
    j = 0
    while j < len(tok) and tok[j].isdigit():
        digits += tok[j]
        j += 1
    rest = tok[j:]
    if not rest or rest[0] not in "RLUDFB":
        return tok
    face = _mirror_face(rest[0])
    return digits + face + rest[1:]


@dataclass(frozen=True)
class FormulaVariant:
    label: str                       # 原式 / 逆式 / 镜像 / 目标缓冲互换 / 共轭 …
    internal_seq: Tuple[str, ...]
    target_swap: bool = False        # 是否交换了目标/缓冲（Flag）


def build_variants(
    internal_seq: Tuple[str, ...],
    *,
    include_inverse: bool = True,
    include_mirror: bool = True,
) -> Tuple[FormulaVariant, ...]:
    """生成原式 / 逆式 / 镜像等变体（不含整体共轭——共轭需结合前置布局，见调用方）。"""
    outs = [FormulaVariant("原式", internal_seq)]
    if include_inverse:
        outs.append(FormulaVariant("逆式", invert_internal(internal_seq)))
    if include_mirror:
        outs.append(FormulaVariant("镜像", tuple(_mirror_token(t) for t in internal_seq)))
        if include_inverse:
            outs.append(FormulaVariant("镜像+逆式", invert_internal(tuple(_mirror_token(t) for t in internal_seq))))
    return tuple(outs)


# ---------------------------------------------------------------------------
# 6. 校准辅助
# ---------------------------------------------------------------------------

def calibrate_formula_roundtrip(formula_seq: Tuple[str, ...], cube_cls=Cube5) -> bool:
    """`公式` 在 solved 上：先用逆式生成状态，再执行公式应回到 solved。

    校验记号适配与观察方向正确（作用于 solved 的严格往返）。
    """
    inv = invert_internal(formula_seq)
    c = cube_cls.solved()
    apply_sourced_sequence(c, inv)
    apply_sourced_sequence(c, formula_seq)
    return c.is_solved()
