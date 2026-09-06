"""free-slice 边缘配对：基于紧凑状态 + 内层切片动作，把目标棱的三块聚到同一槽。

搜索在紧凑态上进行（含 wide + outer + 纯内层切片 3X），用 beam + 关系等级评分。
找到动作序列后，在真实 Cube5 上重放并用 member_slots / is_edge_paired 校验。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from cube.cube5 import Cube5

from .compact_state import CompactPairingState, color_off, state_of, step
from .free_slice import edge_relation, member_slots
from .positions import SLOT_NAMES

# 动作集：compact_state.MOVES 现已含 3X 内层切片。
from .compact_state import MOVES


@dataclass(frozen=True)
class AssemblyResult:
    success: bool
    moves: Tuple[str, ...]
    gathered_slot: Optional[str]
    paired_on_real: bool
    color_off: int


def _beam_search(
    state0: CompactPairingState,
    target_slot: str,
    max_depth: int,
    beam_width: int,
) -> Optional[Tuple[List[str], str]]:
    """在紧凑态上 beam 搜索，找到把 target 三块聚到同一槽的动作序列。

    返回 (move_list, 聚集槽) 或 None。
    """
    if _gathered(state0, target_slot):
        return ([], (member_slots(state0, target_slot)[0]))

    frontier: List[Tuple[CompactPairingState, List[str]]] = [(state0, [])]
    for _ in range(max_depth):
        cand = []
        for st, path in frontier:
            for mv in MOVES:
                st2 = step(st, mv)
                if _gathered(st2, target_slot):
                    ms, _, _ = member_slots(st2, target_slot)
                    return (path + [mv], ms)
                cand.append((st2, path + [mv]))
        # 按 (关系高, 中心错位低) 排序，取 beam_width
        cand.sort(key=lambda t: (-edge_relation(t[0], target_slot).relation, color_off(t[0])))
        frontier = cand[:beam_width]
    return None


def _gathered(state: CompactPairingState, target_slot: str) -> bool:
    ms, wa, wb = member_slots(state, target_slot)
    return ms is not None and ms == wa == wb


def assemble_edge(
    cube: Cube5,
    target_slot: str,
    max_depth: int = 5,
    beam_width: int = 64,
) -> AssemblyResult:
    """在 cube 基础上，用紧凑 beam 搜索找聚拢目标三块的动作，重放校验。"""
    st0 = state_of(cube)
    res = _beam_search(st0, target_slot, max_depth, beam_width)
    if res is None:
        return AssemblyResult(False, (), None, False, color_off(st0))
    moves, gathered_slot = res
    w = cube.clone()
    for mv in moves:
        w.apply_move(mv)
    ms, wa, wb = member_slots(state_of(w), target_slot)
    gathered_real = ms is not None and ms == wa == wb
    return AssemblyResult(
        success=gathered_real,
        moves=tuple(moves),
        gathered_slot=gathered_slot,
        paired_on_real=gathered_real,
        color_off=color_off(state_of(w)),
    )


def restore_centers_keep_gathered(
    state0: CompactPairingState,
    target_slot: str,
    max_depth: int = 6,
    beam_width: int = 96,
    wide_only: bool = False,
) -> Optional[List[str]]:
    """在保持「目标三块同槽」的前提下，把中心 color_off 降到 0。

    wide_only=True 时只用 1层外层+2层宽转（这些动作整组搬运已聚好的三块，不拆散），
    适合「先把边缘聚好、再用宽层+外层回中心」的分阶段策略。
    返回 move 列表（可为空），或 None（未能在深度内降到 0）。
    """
    if color_off(state0) == 0:
        return []
    use_moves = [m for m in MOVES if not (wide_only and m.startswith("3"))]
    frontier: List[Tuple[CompactPairingState, List[str]]] = [(state0, [])]
    for _ in range(max_depth):
        cand = []
        for st, path in frontier:
            for mv in use_moves:
                st2 = step(st, mv)
                if not _gathered(st2, target_slot):
                    continue  # 不许拆散已聚好的三块
                if color_off(st2) == 0:
                    return path + [mv]
                cand.append((st2, path + [mv]))
        cand.sort(key=lambda t: color_off(t[0]))
        frontier = cand[:beam_width]
        if not frontier:
            return None
    return None


def pair_one_edge(
    cube: Cube5,
    target_slot: str,
    max_depth: int = 5,
    beam_width: int = 96,
) -> AssemblyResult:
    """单条：先聚拢三块，再在不拆散的前提下恢复中心到 color_off==0。"""
    st0 = state_of(cube)
    res = _beam_search(st0, target_slot, max_depth, beam_width)
    if res is None:
        return AssemblyResult(False, (), None, False, color_off(st0))
    moves, gathered_slot = res
    st = st0
    for mv in moves:
        st = step(st, mv)
    rest = restore_centers_keep_gathered(st, target_slot)
    if rest is None:
        return AssemblyResult(False, (), None, False, color_off(st))
    full = moves + rest
    w = cube.clone()
    for mv in full:
        w.apply_move(mv)
    ms, wa, wb = member_slots(state_of(w), target_slot)
    gathered_real = ms is not None and ms == wa == wb
    co = color_off(state_of(w))
    return AssemblyResult(
        success=gathered_real and co == 0,
        moves=tuple(full),
        gathered_slot=gathered_slot,
        paired_on_real=gathered_real,
        color_off=co,
    )
