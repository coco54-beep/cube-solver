"""slice-band 模型：活动切片带 + 安全存储槽，全部由 compact 置换自动计算。

对每个自由切片（宽层 quarter 移动 W），离线算出：
- work_slots        该切片装配可用的槽
- split_slots       W/W' 会拆散完整 tredge 的槽
- safe_storage_slots W 与 W' 都不拆散完整组的槽（可安全存放）
- touched_middle/wing_positions 该切片触及的中间/翼位置
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Tuple

from solver.edge5.compact_state import CompactPairingState, step, MOVE_TABLES, MOVES
from solver.edge5.free_slice import _slot_of_mid_idx, _slot_of_wing_idx, target_pieces, MIDDLE_ORDER, WING_ORDER
from solver.edge5.macro_index import _IDENTITY, apply_macro, SLOT_NAMES, SLOT_INDEX

from solver.edge5.positions import slot as logical_slot

# 宽层 quarter 移动（自由切片候选）
WIDE_QUARTER = ["2U", "2U'", "2D", "2D'", "2L", "2L'", "2R", "2R'", "2F", "2F'", "2B", "2B'"]


def inverse_of(mv: str) -> str:
    if mv.endswith("'"):
        return mv[:-1]
    return mv + "'"


def _complete_group_preserved_after(state_after: CompactPairingState, name: str) -> bool:
    tp = target_pieces(name)
    md = _slot_of_mid_idx(state_after, tp.middle_home)
    wa = _slot_of_wing_idx(state_after, tp.wing_a_home)
    wb = _slot_of_wing_idx(state_after, tp.wing_b_home)
    return md is not None and md == wa and md == wb


def _single_move_state(mv: str) -> CompactPairingState:
    return step(_IDENTITY, mv)


def _slot_touched_by_move_single(state_after: CompactPairingState, name: str) -> bool:
    """该移动是否会把槽 name 的三块‘动到别处’（即槽内某块离开该槽）。"""
    tp = target_pieces(name)
    md = _slot_of_mid_idx(state_after, tp.middle_home)
    wa = _slot_of_wing_idx(state_after, tp.wing_a_home)
    wb = _slot_of_wing_idx(state_after, tp.wing_b_home)
    # 若某块被移到非本槽，则触碰了该槽
    return md != name or wa != name or wb != name


@dataclass(frozen=True)
class SliceBand:
    open_move: str
    close_move: str
    work_slots: FrozenSet[str]
    split_slots: FrozenSet[str]
    safe_storage_slots: FrozenSet[str]
    touched_middle_positions: FrozenSet[int]
    touched_wing_positions: FrozenSet[int]
    slot_mask_split: int
    slot_mask_safe: int
    slot_mask_touched: int


def _analyze_band(open_move: str) -> SliceBand:
    close_move = inverse_of(open_move)
    st_open = _single_move_state(open_move)
    st_close = _single_move_state(close_move)

    work = []
    split = []
    safe = []
    mask_split = 0
    mask_safe = 0
    mask_touched = 0
    for i, name in enumerate(SLOT_NAMES):
        # work: 该切片（open 或 close）会触碰/移动该槽 → 可作装配工作槽
        touched = (_slot_touched_by_move_single(st_open, name)
                   or _slot_touched_by_move_single(st_close, name))
        if touched:
            work.append(name)
            mask_touched |= (1 << i)

        # split: open 或 close 会拆散完整组
        sp = (not _complete_group_preserved_after(st_open, name)
              or not _complete_group_preserved_after(st_close, name))
        if sp:
            split.append(name)
            mask_split |= (1 << i)
        else:
            # safe: open 和 close 都完整保留该槽的组
            safe.append(name)
            mask_safe |= (1 << i)

    # touched positions: W 单步置换实际改变的 middle/wing 索引位
    touched_mid = {j for j in range(12) if st_open.middle[j] != _IDENTITY.middle[j]}
    touched_wing = {j for j in range(24) if st_open.wing[j] != _IDENTITY.wing[j]}
    return SliceBand(
        open_move=open_move,
        close_move=close_move,
        work_slots=frozenset(work),
        split_slots=frozenset(split),
        safe_storage_slots=frozenset(safe),
        touched_middle_positions=frozenset(touched_mid),
        touched_wing_positions=frozenset(touched_wing),
        slot_mask_split=mask_split,
        slot_mask_safe=mask_safe,
        slot_mask_touched=mask_touched,
    )


def compute_slice_bands() -> Dict[str, SliceBand]:
    return {w: _analyze_band(w) for w in WIDE_QUARTER}


BANDS: Dict[str, SliceBand] = compute_slice_bands()


def band_for_open(open_move: str) -> SliceBand:
    return BANDS[open_move]
