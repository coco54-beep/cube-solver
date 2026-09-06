"""5x5 free-slice 翼块组装基础（Milestone 3 Foundation）。

标准 free-slice 思路：不要求「单条棱完成后中心立即恢复」。而是
    W（打开自由切片，允许中心被打乱）
    A（若干外层动作，搬运/暂存翼块）
    W'（关闭自由切片）
    —— 批次末统一恢复中心。

本模块提供：
- FreeSliceState：自由切片状态（活动轴、偏移量、工作/暂存槽等）。
- FreeSliceMacroEffect：宏的完整效果分析（中心、目标中/翼增量、配对增减、触及槽）。
- 关系级评价：目标中棱 + 两个翼之间的「聚集关系等级」（0~3），
  而非只数完整配对。
- W + outer + W' 宏枚举器（在紧凑状态上快速求值）。
- WHOLE_EDGE_SWAP_MAIN：整条已配棱搬移宏（中心保持）。

只读、无副作用；所有宏都应在完整 Cube5 上重放校验。
"""

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from .compact_state import (
    CompactPairingState,
    MOVE_TABLES,
    MOVES,
    _SLOT_MID,
    _SLOT_WINGS,
    _SLOT_POS,
    _POS_HOME_SLOT,
    MIDDLE_ORDER,
    WING_ORDER,
    MIDDLE_INDEX,
    WING_INDEX,
    slot,
    color_off,
)
from .positions import SLOT_NAMES

# --- 关系 / 效果类型 -------------------------------------------------------

# 聚集关系等级
#   0: 三块完全分散
#   1: 一个目标翼与中棱进入同一逻辑槽关系
#   2: 形成可暂存的中棱 + 单翼二块组合
#   3: 两个翼都与中棱聚集（完整/可成完整配对）
REL_SCATTERED = 0
REL_ONE_WING = 1
REL_COMBO = 2
REL_PAIRED = 3


@dataclass(frozen=True)
class FreeSliceState:
    """自由切片状态。"""

    active_axis: Optional[int]          # 当前自由切片所属轴 0=X 1=Y 2=Z；None=未打开
    slice_offset: int                   # 切片相对初始位置的转量 0..3 quarter turns
    work_slot: str                      # 工作中棱槽
    buffer_slot: str                    # 暂存槽
    staged_pairs: Tuple = ()            # 已暂存组合（中棱+翼的 home 色对）
    protected_groups: Tuple = ()        # 已配棱组（整条已配，需保护）


@dataclass(frozen=True)
class TargetPieces:
    """目标棱的 3 个成员（按 home 槽描述）。"""

    home_slot: str
    middle_home: int
    wing_a_home: int
    wing_b_home: int


@dataclass(frozen=True)
class EdgeAssemblyRelation:
    """目标中棱与两翼之间的聚集关系（及是否在切片恢复后仍成立）。"""

    middle_slot: Optional[str]
    wing_a_relation: int
    wing_b_relation: int
    relation: int                      # 本次评价的最高等级
    survives_slice_restore: bool
    all_in_one_slot: bool


@dataclass(frozen=True)
class FreeSliceMacroEffect:
    """宏的完整效果分析。"""

    moves: Tuple[str, ...]
    centers_color_solved_after: bool
    fixed_centers_preserved: bool
    target_middle_delta: Tuple[str, str]          # (before_slot, after_slot)
    target_wing_a_delta: Tuple[Optional[str], Optional[str]]
    target_wing_b_delta: Tuple[Optional[str], Optional[str]]
    relation_before: int
    relation_after: int
    paired_groups_created: int
    paired_groups_broken: int
    touched_slots: FrozenSet[str]


# --- 紧凑状态访问小工具 ----------------------------------------------------

def target_pieces(home_slot: str) -> TargetPieces:
    return TargetPieces(
        home_slot=home_slot,
        middle_home=_SLOT_MID[home_slot],
        wing_a_home=_SLOT_WINGS[home_slot][0],
        wing_b_home=_SLOT_WINGS[home_slot][1],
    )


def _slot_of_wing_idx(state: CompactPairingState, wing_home: int) -> Optional[str]:
    for j, v in enumerate(state.wing):
        if v == wing_home:
            return _POS_HOME_SLOT[WING_ORDER[j]]
    return None


def _slot_of_mid_idx(state: CompactPairingState, mid_home: int) -> Optional[str]:
    for j, v in enumerate(state.middle):
        if v == mid_home:
            return _POS_HOME_SLOT[MIDDLE_ORDER[j]]
    return None


def member_slots(state: CompactPairingState, home_slot: str):
    """返回 (中椛槽, 翼a槽, 翼b槽)。"""
    tp = target_pieces(home_slot)
    return (
        _slot_of_mid_idx(state, tp.middle_home),
        _slot_of_wing_idx(state, tp.wing_a_home),
        _slot_of_wing_idx(state, tp.wing_b_home),
    )


def edge_relation(state: CompactPairingState, home_slot: str) -> EdgeAssemblyRelation:
    """评价目标棱（home_slot）的中棱与两翼之间的聚集关系等级。"""
    tp = target_pieces(home_slot)
    mid_slot = _slot_of_mid_idx(state, tp.middle_home)
    wa_slot = _slot_of_wing_idx(state, tp.wing_a_home)
    wb_slot = _slot_of_wing_idx(state, tp.wing_b_home)

    # 与中棱同一槽的翼数
    n_same = 0
    if mid_slot is not None:
        if wa_slot == mid_slot:
            n_same += 1
        if wb_slot == mid_slot:
            n_same += 1

    if n_same == 0:
        rel = REL_SCATTERED
    elif n_same == 1:
        rel = REL_COMBO
    else:
        rel = REL_PAIRED

    all_in_one = (mid_slot is not None and wa_slot == mid_slot and wb_slot == mid_slot)

    w_a_rel = REL_ONE_WING if wa_slot == mid_slot else REL_SCATTERED
    w_b_rel = REL_ONE_WING if wb_slot == mid_slot else REL_SCATTERED

    return EdgeAssemblyRelation(
        middle_slot=mid_slot,
        wing_a_relation=w_a_rel,
        wing_b_relation=w_b_rel,
        relation=rel,
        survives_slice_restore=True,  # 由构造决定：W' 始终包含在宏内
        all_in_one_slot=all_in_one,
    )


def _fixed_center_home_set(cube) -> frozenset:
    return frozenset(
        p for p, c in cube.cubies.items()
        if len(c.stickers) == 1 and sorted(abs(v) for v in c.home) == [0, 0, 6]
    )


def _fixed_centers_preserved(cube) -> bool:
    fixed = _fixed_center_home_set(cube)
    return all(cube.cubies[p].pos == p for p in fixed)


# --- 宏效果分析 -------------------------------------------------------------

def analyze_macro(
    cube,
    moves: Sequence[str],
    target_home_slot: str,
) -> FreeSliceMacroEffect:
    """在完整 Cube5 上重放宏，并给出完整效果报告（不改动输入 cube）。

    计算：中心是否最终按颜色归面、固定面心是否保持、目标中/两翼个别的
    前后槽位、配对槽数增减、触及槽集合。
    """
    from .compact_state import state_of
    from .state import center_color_off, is_edge_paired
    from .positions import SLOT_NAMES
    from . import free_slice as _fs

    work = cube.clone()
    st_before = state_of(cube)
    tp = target_pieces(target_home_slot)

    rel_before = edge_relation(st_before, target_home_slot)
    mb_before, wa_before, wb_before = member_slots(st_before, target_home_slot)
    before_paired = set(s for s in SLOT_NAMES if is_edge_paired(cube, s))

    for mv in moves:
        work.apply_move(mv)
    st_after = state_of(work)
    rel_after = edge_relation(st_after, target_home_slot)
    mb_after, wa_after, wb_after = member_slots(st_after, target_home_slot)

    after_paired = set(s for s in SLOT_NAMES if is_edge_paired(work, s))
    centers_solved = center_color_off(work) == 0
    fixed_preserved = _fixed_centers_preserved(work)

    return FreeSliceMacroEffect(
        moves=tuple(moves),
        centers_color_solved_after=centers_solved,
        fixed_centers_preserved=fixed_preserved,
        target_middle_delta=(mb_before, mb_after),
        target_wing_a_delta=(wa_before, wa_after),
        target_wing_b_delta=(wb_before, wb_after),
        relation_before=rel_before.relation,
        relation_after=rel_after.relation,
        paired_groups_created=len(after_paired - before_paired),
        paired_groups_broken=len(before_paired - after_paired),
        touched_slots=frozenset(before_paired | after_paired),
    )


# --- W + outer + W' 宏枚举器 -------------------------------------------------

_OUTER = [m for m in MOVES if not m[:1].isdigit()]
_WIDE = [m for m in MOVES if m[:1].isdigit()]


def _inv(mv: str) -> str:
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    return mv + "'"


def _apply_perm(perm, mv, table):
    return tuple(perm[table[mv][j]] for j in range(len(perm)))


def enumerate_wide_outer_wide_compact(
    max_outer: int,
    target_home_slot: str,
    start: Optional[CompactPairingState] = None,
) -> List[Tuple[Tuple[str, ...], int, int, bool]]:
    """枚举 W + outer^(1..max_outer) + W' 宏，在紧凑状态上求关系等级与中心。

    返回 (moves, relation_after, color_off_after, relation_improved)。
    relation_improved 以 start（默认身份=已还原）的 before 关系为参照。
    只用紧凑置换，不克隆 Cube5。
    """
    from itertools import product
    pm = {mv: MOVE_TABLES[mv][0] for mv in MOVES}
    pw = {mv: MOVE_TABLES[mv][1] for mv in MOVES}
    pc = {mv: MOVE_TABLES[mv][2] for mv in MOVES}

    if start is None:
        start = CompactPairingState(tuple(range(12)), tuple(range(24)), tuple(range(54)))
    rel_before = edge_relation(start, target_home_slot)
    base_rel = rel_before.relation

    out = []
    for w in _WIDE:
        wq = _inv(w)
        for A_len in range(1, max_outer + 1):
            for A in product(_OUTER, repeat=A_len):
                seq = (w,) + A + (wq,)
                mid = start.middle
                wing = start.wing
                cp = start.center
                for mv in seq:
                    mid = _apply_perm(mid, mv, pm)
                    wing = _apply_perm(wing, mv, pw)
                    cp = _apply_perm(cp, mv, pc)
                st = CompactPairingState(mid, wing, cp)
                rel = edge_relation(st, target_home_slot)
                co = color_off(st)
                improved = rel.relation > base_rel
                out.append((seq, rel.relation, co, improved))
    return out


# --- 受控分散态构造 ----------------------------------------------------------

def controlled_start(target_home_slot: str, entry_pos) -> CompactPairingState:
    """构造受控分散态：目标中棱在 home、目标翼-a 移到 entry_pos、中心身份一致。

    entry_pos 必须是合法翼坐标（两个 ±6，一个 ±3）。
    """
    mid = tuple(range(12))
    wing = list(range(24))
    wa_home = _SLOT_WINGS[target_home_slot][0]
    e_idx = WING_INDEX[entry_pos]
    wing[wa_home], wing[e_idx] = wing[e_idx], wing[wa_home]
    cen = tuple(range(54))
    return CompactPairingState(tuple(mid), tuple(wing), cen)


# --- 整条已配棱搬移宏 -------------------------------------------------------

# 中心保持的整条已配棱搬移宏：成对交换整条棱三元组。
#   作用：BL<->BR, FL<->FR, DB<->UB, DF<->UF
#   每条棱的 3 块（中 + 两翼）一体搬运，已配组不被拆散；中心 color_off 保持 0。
WHOLE_EDGE_SWAP_MAIN: Tuple[str, ...] = ("2B", "B2", "F2", "2B'")

WHOLE_EDGE_SWAP_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("BL", "BR"),
    ("FL", "FR"),
    ("DB", "UB"),
    ("DF", "UF"),
)


def whole_edge_swap_effect(cube) -> Dict[str, Dict[str, str]]:
    """在完整 Cube5 上重放 WHOLE_EDGE_SWAP_MAIN，报告每对整棱的搬运映射。"""
    from .compact_state import state_of
    st_before = state_of(cube)
    work = cube.clone()
    for mv in WHOLE_EDGE_SWAP_MAIN:
        work.apply_move(mv)
    st_after = state_of(work)

    mapping = {}
    for a, b in WHOLE_EDGE_SWAP_PAIRS:
        ma_before = _slot_of_mid_idx(st_before, _SLOT_MID[a])
        mb_before = _slot_of_mid_idx(st_before, _SLOT_MID[b])
        ma_after = _slot_of_mid_idx(st_after, _SLOT_MID[a])
        mb_after = _slot_of_mid_idx(st_after, _SLOT_MID[b])
        mapping[(a, b)] = {
            "a_before": ma_before, "a_after": ma_after,
            "b_before": mb_before, "b_after": mb_after,
        }
    return mapping
