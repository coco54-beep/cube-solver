"""纯外层(outer-moves)存储规划器：把完整配对组整体搬入安全存储槽。

外层动作会把完整 tredge 当作整体搬运（保持同槽、朝向一致、中心颜色归面），
因此可用精简的「槽图」BFS：状态 = 组当前所属逻辑槽，动作 = 单个外层移动。

目标：group 的当前槽 ∈ band.safe_storage_slots，并在真实 Cube5 上验证。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from cube.cube5 import Cube5
from solver.edge5.compact_state import state_of
from solver.edge5.free_slice import _slot_of_mid_idx, _slot_of_wing_idx, target_pieces, MIDDLE_ORDER, WING_ORDER
from solver.edge5.macro_index import _IDENTITY, apply_macro
from solver.edge5.slice_band import SliceBand
from solver.edge5.positions import SLOT_NAMES
from solver.edge5.pairing_transaction import ProtectedTredge, is_tredge_group_paired
from solver.edge5.state import centers_are_color_solved

OUTER_MOVES = [
    "U", "U'", "U2", "D", "D'", "D2", "L", "L'", "L2",
    "R", "R'", "R2", "F", "F'", "F2", "B", "B'", "B2",
]
_OUTER_INV = {m: (m[:-1] if m.endswith("'") else m + "'")
              for m in OUTER_MOVES}
_OUTER_INV.update({m: m for m in OUTER_MOVES if m.endswith("2")})


def _slot_after_outer(name: str, mv: str) -> Optional[str]:
    """在外层动作 mv 作用下，槽 name 的完整组被搬到哪个槽（若保持同槽）。"""
    tp = target_pieces(name)
    st = apply_macro(_IDENTITY, (mv,))
    md = _slot_of_mid_idx(st, tp.middle_home)
    wa = _slot_of_wing_idx(st, tp.wing_a_home)
    wb = _slot_of_wing_idx(st, tp.wing_b_home)
    if md is not None and md == wa == wb:
        return md
    return None  # 该外层动作拆散了该槽组（不应出现在图上）


# 槽图：slot -> {mv: dst_slot}
_SLOT_GRAPH = {}
for name in SLOT_NAMES:
    edges = {}
    for mv in OUTER_MOVES:
        d = _slot_after_outer(name, mv)
        if d is not None:
            edges[mv] = d
    _SLOT_GRAPH[name] = edges


def group_current_slot(cube: Cube5, group: ProtectedTredge) -> Optional[str]:
    st = state_of(cube)
    try:
        mid_idx = MIDDLE_ORDER.index(group.middle_piece_id)
    except ValueError:
        # middle_piece_id 可能已是索引；兜底直接当索引
        mid_idx = group.middle_piece_id
    if isinstance(mid_idx, int):
        return _slot_of_mid_idx(st, mid_idx)
    return None


@dataclass(frozen=True)
class StoreResult:
    success: bool
    moves: Tuple[str, ...]
    source_slot: str
    destination_slot: str
    protected_group: ProtectedTredge
    group_preserved: bool
    destination_safe_for_band: bool
    centers_color_solved: bool
    error_code: Optional[str] = None


def _bfs_slot_path(start: str, safe_slots, max_depth: int = 4):
    from collections import deque
    if start in safe_slots:
        return ()
    q = deque()
    q.append((start, []))
    seen = {start}
    while q:
        s, path = q.popleft()
        if len(path) >= max_depth:
            continue
        for mv, dst in _SLOT_GRAPH[s].items():
            if dst in seen:
                continue
            newpath = path + [mv]
            if dst in safe_slots:
                return tuple(newpath)
            seen.add(dst)
            q.append((dst, newpath))
    return None


def enumerate_store_paths(
    cube: Cube5,
    group: ProtectedTredge,
    active_band: SliceBand,
    max_depth: int = 4,
    require_centers_solved: bool = True,
) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """枚举把 group 用纯外层动作整体搬到 band.safe_storage_slots 的全部短路径。

    返回 ``((destination_slot, moves), ...)``，按字典序稳定排序，并已在真实
    Cube5 上验证（组完整保留 + 落在安全槽）。当 ``require_centers_solved`` 为
    True 时额外要求中心颜色归面（关闭态）；打开切片态中心本就不归面，应传 False。
    """
    src = group_current_slot(cube, group)
    if src is None:
        return ()
    safe = active_band.safe_storage_slots

    from collections import deque
    out = []
    if src in safe:
        out.append((src, ()))
    q = deque()
    q.append((src, ()))
    seen = {src}
    while q:
        s, path = q.popleft()
        if len(path) >= max_depth:
            continue
        for mv, dst in _SLOT_GRAPH[s].items():
            if dst in seen:
                continue
            newpath = path + (mv,)
            if dst in safe:
                # 真实重放验证
                w = cube.clone()
                for m in newpath:
                    w.apply_move(m)
                if (is_tredge_group_paired(w, group)
                        and group_current_slot(w, group) == dst
                        and (not require_centers_solved
                             or centers_are_color_solved(w))):
                    out.append((dst, tuple(newpath)))
            seen.add(dst)
            q.append((dst, newpath))
    out.sort(key=lambda t: (len(t[1]), t[0], t[1]))
    return tuple(out)


def store_paired_tredge(
    cube: Cube5,
    group: ProtectedTredge,
    active_band: SliceBand,
    max_depth: int = 4,
) -> StoreResult:
    src = group_current_slot(cube, group)
    if src is None:
        return StoreResult(False, (), "", "", group, False, False, False, "group_not_located")
    safe = active_band.safe_storage_slots
    if src in safe:
        # 已在安全槽，无需移动
        return StoreResult(True, (), src, src, group, True, True,
                           centers_are_color_solved(cube))
    path = _bfs_slot_path(src, safe, max_depth)
    if path is None:
        return StoreResult(False, (), src, "", group, False, False, False,
                           f"no_outer_path_{src}->safe")

    # 真实 Cube5 重放验证
    w = cube.clone()
    for mv in path:
        w.apply_move(mv)
    preserved = is_tredge_group_paired(w, group)
    dst = group_current_slot(w, group)
    safe_ok = dst in active_band.safe_storage_slots
    center_ok = centers_are_color_solved(w)
    ok = preserved and safe_ok and center_ok
    return StoreResult(
        success=ok,
        moves=tuple(path),
        source_slot=src,
        destination_slot=dst,
        protected_group=group,
        group_preserved=preserved,
        destination_safe_for_band=safe_ok,
        centers_color_solved=center_ok,
    )
