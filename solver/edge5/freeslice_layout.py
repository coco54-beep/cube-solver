"""确定性 free-slice 固定工作布局（Gate 2）。

为 free-slice 配棱选一套**固定**工作布局（不随对称泛化），在 compact 位置态上
离线预计算「纯外层（仅 1X）定位表」，使得——

- 任意目标**中棱**可由纯外层 setup 移到工作槽；
- 任意目标**翼**可由纯外层 setup 移到有限入口（UR 翼位）；
- 纯外层动作天然保持中心颜色归面与固定面心。

定位表以「piece 当前所在位置下标」为键（纯外层是纯位置置换，与 piece 身份无关，
故对任意 piece 均正确）。只读、无副作用；所有定位序列最终须在真实 Cube5 上重放校验。

背景（关键认知）：
- 只有外层 1X 在中心归面时保持 centers_are_color_solved；宽转 2X 会破坏中心归面。
- 因此「定位 setup」只用纯外层 1X；真正的 free-slice 用 2U + outer + 2U'（开/关切片）。
- 正式搜索动作集为 36 个 1X/2X（不含 3X/4X/5X，它们会移动固定面心）。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, Tuple

from .compact_state import MOVE_TABLES
from .positions import (
    SLOT_NAMES, MIDDLE_ORDER, WING_ORDER, MIDDLE_INDEX, WING_INDEX,
    slot,
)

# 纯外层动作（1X）：定位 setup 只用这些。
OUTER_MOVES: Tuple[str, ...] = (
    "R", "L", "U", "D", "F", "B",
    "R'", "L'", "U'", "D'", "F'", "B'",
    "R2", "L2", "U2", "D2", "F2", "B2",
)


def _slot_middle(name: str):
    return slot(name).middle


def _invert_perm(perm: Tuple[int, ...]) -> Tuple[int, ...]:
    inv = [0] * len(perm)
    for i, v in enumerate(perm):
        inv[v] = i
    return tuple(inv)


def _outer_forward_perms():
    fwd = {}
    for mv in OUTER_MOVES:
        fwd[mv] = (_invert_perm(MOVE_TABLES[mv][0]), _invert_perm(MOVE_TABLES[mv][1]))
    return fwd


_FWD = _outer_forward_perms()


def _bfs_outer_idx(source_index: int, target_index: int, idx_perm, max_depth: int):
    """求把「位于 source_index 的 piece」移到 target_index 的最短纯外层序列。"""
    if source_index == target_index:
        return ()
    frontier = deque([(source_index, ())])
    seen = {source_index}
    while frontier:
        idx, path = frontier.popleft()
        if len(path) >= max_depth:
            continue
        for mv in OUTER_MOVES:
            nxt = idx_perm[mv][idx]
            if nxt in seen:
                continue
            newpath = path + (mv,)
            if nxt == target_index:
                return newpath
            seen.add(nxt)
            frontier.append((nxt, newpath))
    return None


@dataclass(frozen=True)
class FreeSliceLayout:
    """固定 free-slice 工作布局（字段遵循 Gate 2 说明）。"""

    name: str
    work_slot: str
    middle_target_slot: str
    wing_entry_slots: Tuple[str, ...]
    staging_slots: Tuple[str, ...]
    storage_slots: Tuple[str, ...]
    open_move: str
    close_move: str
    touched_slots_mask: int
    safe_storage_mask: int

    # 定位表（位置下标为键；纯外层序列把该位置的 piece 移到目标位置）
    middle_to_work: Dict[int, Tuple[str, ...]]
    wing_to_entry: Dict[int, Tuple[str, ...]]


def build_layout(
    work_slot: str = "UF",
    open_move: str = "2U",
    entry_slots: Tuple[str, ...] = ("UR",),
    max_depth: int = 8,
) -> FreeSliceLayout:
    """构建固定工作布局，并预计算纯外层定位表（位置下标为键）。

    touched_slots_mask / safe_storage_mask 以及存储/暂存槽取自 slice_band 对
    open_move 的分析（见 solver.edge5.slice_band.BANDS）。
    """
    from .slice_band import band_for_open
    close_move = open_move[:-1] if open_move.endswith("'") else open_move + "'"
    band = band_for_open(open_move)
    # 暂存 = 该切片带中被触碰但仍保留完整组的槽（可用于放部分组合）；
    # 安全存储 = open/close 都完整保留的槽。
    staging_slots = tuple(sorted(band.work_slots))
    storage_slots = tuple(sorted(band.safe_storage_slots))
    mid_perms = {mv: _FWD[mv][0] for mv in OUTER_MOVES}
    wing_perms = {mv: _FWD[mv][1] for mv in OUTER_MOVES}

    work_mid_pos = MIDDLE_INDEX[_slot_middle(work_slot)]
    middle_to_work = {}
    for i in range(len(MIDDLE_ORDER)):
        seq = _bfs_outer_idx(i, work_mid_pos, mid_perms, max_depth)
        if seq is not None:
            middle_to_work[i] = seq

    # 入口 = 第一个入口槽的右翼位置（若空则左翼）
    if entry_slots:
        entry_slot = entry_slots[0]
        entry_wing_pos = WING_INDEX[slot(entry_slot).right_wing]
    else:
        entry_wing_pos = WING_INDEX[slot("UR").right_wing]
    wing_to_entry = {}
    for i in range(len(WING_ORDER)):
        seq = _bfs_outer_idx(i, entry_wing_pos, wing_perms, max_depth)
        if seq is not None:
            wing_to_entry[i] = seq

    return FreeSliceLayout(
        name="uf-u-band",
        work_slot=work_slot,
        middle_target_slot=work_slot,
        wing_entry_slots=entry_slots,
        staging_slots=staging_slots,
        storage_slots=storage_slots,
        open_move=open_move,
        close_move=close_move,
        touched_slots_mask=band.slot_mask_touched,
        safe_storage_mask=band.slot_mask_safe,
        middle_to_work=middle_to_work,
        wing_to_entry=wing_to_entry,
    )


# 模块级默认布局（导入时构建，纯外层 BFS 很快）
DEFAULT_LAYOUT: FreeSliceLayout = build_layout()
