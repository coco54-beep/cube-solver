"""Gate 5b · 双棱规范化布局（目标 A→UF，缓冲 B→UR/UB/UL）。

用纯外层动作把目标 A（已装配的翻转三块组）**整体**搬到固定槽 UF，并把缓冲 B 的
中棱（或其局部组）搬到允许缓冲槽 UR/UB/UL。只读，不修改传入 cube。

**关键认知**：纯外层动作会**耦合同一层所有 piece**（先搬目标 A 再单独搬缓冲 B 会互相
破坏——缓冲的 `U` 会把目标 A 又挪走）。因此必须对**四元组**（目标中棱, 目标翼A, 目标翼B,
缓冲中棱）做**联合 setup**（`_bfs_n`），把整组一起搬到目标排布 `(UF, 缓冲槽)`，才能避免
`JOINT_SETUP_UNREACHABLE`，也无需假设目标三块在纯外层下保持同一槽。

**候选槽对**：因纯外层未必能把任意有序槽对同时映射到指定的 (UF, UR)，目标集合允许
`(UF, UR) / (UF, UB) / (UF, UL)`，避免再次制造 `JOINT_SETUP_UNREACHABLE`。

本模块只负责"规范化布局"，不修正翻转。规范后的翻转由 Gate 5b 公式适配（`formula_adapter`）
在这一**固定布局**下处理。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .compact_state import MOVE_TABLES
from .freeslice_layout import OUTER_MOVES
from .positions import MIDDLE_INDEX, WING_INDEX, slot

TARGET_SLOT = "UF"
BUFFER_SLOTS: Tuple[str, ...] = ("UR", "UB", "UL")

# 纯外层前向置换（中/翼）：new_pos = perm[old_pos]。
_FWD: Dict[str, Tuple[Tuple[int, ...], Tuple[int, ...]]] = {}


def _invert_perm(perm: Tuple[int, ...]) -> Tuple[int, ...]:
    inv = [0] * len(perm)
    for i, v in enumerate(perm):
        inv[v] = i
    return tuple(inv)


def _build_fwd():
    global _FWD
    if _FWD:
        return
    for mv in OUTER_MOVES:
        _FWD[mv] = (_invert_perm(MOVE_TABLES[mv][0]), _invert_perm(MOVE_TABLES[mv][1]))


def _invert_move(mv: str) -> str:
    if mv.endswith("2"):
        return mv
    if mv.endswith("'"):
        return mv[:-1]
    return mv + "'"


def _invert_sequence(seq: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(_invert_move(m) for m in reversed(seq))


def _apply(seq, start):
    pos = start
    for mv in seq:
        fm, fw = _FWD[mv]
        pos = (fm[pos[0]], fw[pos[1]], fw[pos[2]])
    return pos


def _bfs_n(start, target, n: int, max_depth: int):
    """用纯外层把 `n` 个点（首点走 mid 置换，其余走 wing 置换）同时送到 target。"""
    _build_fwd()
    if start == target:
        return ()
    frontier = deque([(start, ())])
    seen = {start}
    while frontier:
        pos, path = frontier.popleft()
        if len(path) >= max_depth:
            continue
        for mv in OUTER_MOVES:
            fm, fw = _FWD[mv]
            nxt = [fm[pos[0]]] + [fw[p] for p in pos[1:]]
            nxt = tuple(nxt)
            if nxt in seen:
                continue
            seen.add(nxt)
            np = path + (mv,)
            if nxt == target:
                return np
            frontier.append((nxt, np))
    return None


@dataclass(frozen=True)
class FlipTransferLayout:
    """一次 Gate 5b 规范化布局：目标 A → `target_slot`，缓冲 B → `buffer_slot`。"""

    target_slot: str                       # 固定 UF
    buffer_slots: Tuple[str, ...]          # 允许的缓冲槽集合
    target_setup_moves: Tuple[str, ...]    # 目标 A 三块整体 -> UF
    inverse_target_setup_moves: Tuple[str, ...]
    buffer_setup_moves: Tuple[str, ...]    # 缓冲 B 中棱 -> buffer_slot
    buffer_slot: Optional[str]             # 实际选定（None = 未达）

    @property
    def combined_setup(self) -> Tuple[str, ...]:
        return self.target_setup_moves + self.buffer_setup_moves

    @property
    def inverse_combined_setup(self) -> Tuple[str, ...]:
        return _invert_sequence(self.combined_setup)


@dataclass(frozen=True)
class FlipLayoutResult:
    success: bool
    layout: Optional[FlipTransferLayout]
    error_code: Optional[str]
    target_pieces_gathered: bool
    buffer_middle_reachable: bool
    message: str

    @property
    def setup_moves(self) -> Tuple[str, ...]:
        return self.layout.combined_setup if (self.success and self.layout) else ()


def normalize_flip_transfer(
    cube,
    *,
    target_middle_home: int,
    target_wing_a_home: int,
    target_wing_b_home: int,
    buffer_middle_home: int,
    max_depth: int = 10,
) -> FlipLayoutResult:
    """把目标 A 三块整体搬到 UF、缓冲 B 中棱搬到允许缓冲槽。只读。

    `*_home` 均为**home 下标**（整数，见 `MIDDLE_INDEX`/`WING_INDEX`，与 compact 态一致）。
    成功条件：目标三块各自当前位置能经纯外层整体搬到 UF 的三个位置，
    且缓冲中棱能搬到某允许缓冲槽；中心仍归面、固定面心不动。
    """
    from .state import centers_are_color_solved
    from .free_slice import _fixed_centers_preserved
    from .compact_state import state_of

    _build_fwd()
    st = state_of(cube)

    def cur_pos_idx(kind_perm, home):
        return next((j for j, v in enumerate(kind_perm) if v == home), None)

    m0 = cur_pos_idx(st.middle, target_middle_home)
    a0 = cur_pos_idx(st.wing, target_wing_a_home)
    b0 = cur_pos_idx(st.wing, target_wing_b_home)
    bm0 = cur_pos_idx(st.middle, buffer_middle_home)
    if m0 is None or a0 is None or b0 is None:
        return FlipLayoutResult(False, None, "TARGET_PIECE_MISSING", False, False,
                                "目标 A 某 piece 缺失")
    if bm0 is None:
        return FlipLayoutResult(False, None, "BUFFER_PIECE_MISSING", True, False,
                                "缓冲 B 中棱缺失")

    t_slot = slot(TARGET_SLOT)
    t_mid = MIDDLE_INDEX[t_slot.middle]
    t_wing_l = WING_INDEX[t_slot.left_wing]
    t_wing_r = WING_INDEX[t_slot.right_wing]

    # 联合 setup：纯外层动作会耦合同层所有 piece，故不可独立搬目标/缓冲；
    # 必须对四元组 (目标中棱, 目标翼A, 目标翼B, 缓冲中棱) 一起 BFS 到目标排布，
    # 才能避免「先搬 A 再搬 B 互相破坏」。
    start = (m0, a0, b0, bm0)
    for bs in BUFFER_SLOTS:
        tbuf = MIDDLE_INDEX[slot(bs).middle]
        goal = (t_mid, t_wing_l, t_wing_r, tbuf)
        seq = _bfs_n(start, goal, 4, max_depth)
        if seq is not None:
            layout = FlipTransferLayout(
                target_slot=TARGET_SLOT,
                buffer_slots=BUFFER_SLOTS,
                target_setup_moves=tuple(seq),
                inverse_target_setup_moves=_invert_sequence(tuple(seq)),
                buffer_setup_moves=(),
                buffer_slot=bs,
            )
            return FlipLayoutResult(True, layout, None, True, True, "ok")

    return FlipLayoutResult(False, None, "SETUP_UNREACHABLE",
                            True, True, "四元组无法用纯外层同时搬到 (UF, 缓冲槽)")
