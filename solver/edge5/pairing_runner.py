"""5x5 配棱器（收敛贪心）。

策略：用 `assemble_edge`（inner-slice beam）逐条把目标三块聚成配对槽。
为保证单调收敛，每次操作**只接受「配对槽数严格增加」的结果**；若某次装配
导致其它已配槽被拆（配对数不增、甚至下降），则回退到操作前状态并换目标重试。

这保证配对数不下降；当没有能「净增」配对的候选时即停（返回当前进度，不假装完全
配对成功）。配不齐时由上层返回结构化错误（EDGE_PAIRING_INCOMPLETE）。

只读输入，不修改传入 cube；返回动作序列。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from cube.cube5 import Cube5

from .compact_state import state_of
from .free_slice import member_slots
from .free_slice_pair import assemble_edge
from .positions import SLOT_NAMES
from .state import is_edge_paired, paired_count


@dataclass(frozen=True)
class EdgePairingResult:
    success: bool
    moves: Tuple[str, ...]
    paired: int
    error_code: Optional[str] = None
    message: str = ""


def _target_gathered(cube: Cube5, s: str) -> bool:
    ms, wa, wb = member_slots(state_of(cube), s)
    return ms is not None and ms == wa == wb


def _choose_targets(cube: Cube5) -> List[str]:
    """候选目标：优先选「未聚拢且该槽未配对」的，其次未配对槽。"""
    out = []
    for s in SLOT_NAMES:
        if is_edge_paired(cube, s):
            continue
        if _target_gathered(cube, s):
            continue
        out.append(s)
    return out


def pair_all_edges(
    cube: Cube5,
    target_count: int = 12,
    max_iter: int = 36,
    max_depth: int = 5,
    beam_width: int = 96,
) -> EdgePairingResult:
    """尽力单调配齐到 target_count。返回结果与动作（不修改输入）。"""
    work = cube.clone()
    allmoves: List[str] = []
    for _ in range(max_iter):
        if paired_count(work) >= target_count:
            break
        before = paired_count(work)
        improved = False
        for tgt in _choose_targets(work):
            backup = work.clone()
            res = assemble_edge(work, tgt, max_depth=max_depth, beam_width=beam_width)
            if not res.success:
                continue
            work.apply_moves(res.moves)
            if paired_count(work) > before:
                allmoves.extend(res.moves)
                improved = True
                break
            # 回退：本次操作未净增配对
            work = backup
        if not improved:
            break
    paired = paired_count(work)
    ok = paired >= target_count
    return EdgePairingResult(
        success=ok,
        moves=tuple(allmoves),
        paired=paired,
        error_code=None if ok else "EDGE_PAIRING_INCOMPLETE",
        message="配齐 %d 条" % paired if ok else "仅配对 %d/%d 条" % (paired, target_count),
    )
