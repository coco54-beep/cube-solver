"""M2.5：联合穿谷分桶 beam 搜索，破解深打乱单棱构造。

联合目标（plan §3.1）：
    is_edge_paired(cube, target_type) 且  centers_are_color_solved(cube)

在紧凑态（CompactPairingState）上做 valley 分桶 beam（§3.3），允许：
- 目标三块暂时聚集后又拆散；
- 中心错位暂时增加；
- 匹配数从3退回2/1/0。

紧凑态上「目标三块同槽」即等价于该逻辑棱颜色配对（三块为同一类型，共处即配好）。
联合目标 = edge_relation(cs, target).relation == 3 AND color_off(cs) == 0。

每条候选路径最终在真实 Cube5 上重放并校验 is_edge_paired + centers_are_color_solved。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from cube.cube5 import Cube5
from solver.center5 import solve_centers5
from solver.center5.legal_moves import LEGAL_5X5_CENTER_MOVES

from .compact_state import CompactPairingState, color_off, state_of, step
from .free_slice import edge_relation, member_slots
from .positions import SLOT_NAMES

# 动作集：含 1层外层 + 2层宽转 + 3X 内层切片（experiment H 证明必需）。
from .compact_state import MOVES

GOAL_REL = 3


@dataclass(frozen=True)
class JointResult:
    success: bool
    moves: Tuple[str, ...]
    error_code: Optional[str]
    nodes: int
    depth: int


def _is_goal(st: CompactPairingState, target_slot: str) -> bool:
    return edge_relation(st, target_slot).relation == GOAL_REL and color_off(st) == 0


def _bucket_key(st: CompactPairingState, target_slot: str) -> Tuple[int, int]:
    """(目标匹配成员数 0/1/2/3, 中心错位桶 0/1-8/9-16/17-24/25+)。"""
    rel = edge_relation(st, target_slot).relation
    co = color_off(st)
    if co == 0:
        cb = 0
    elif co <= 8:
        cb = 1
    elif co <= 16:
        cb = 2
    elif co <= 24:
        cb = 3
    else:
        cb = 4
    return (rel, cb)


def _open_move_safe(cand_path: List[str], mv: str) -> bool:
    """安全剪枝（§3.5）：避免立即执行逆动作/同一面连续等，仅保守处理。"""
    if not cand_path:
        return True
    return True  # 第一版不激进剪枝，防止错剪丢失解


def joint_search(
    state0: CompactPairingState,
    target_slot: str,
    max_depth: int = 8,
    per_bucket: int = 16,
    max_buckets: int = 64,
) -> Tuple[Optional[List[str]], int]:
    """谷式分桶 beam。返回 (move_list, nodes) 或 (None, nodes)。"""
    if _is_goal(state0, target_slot):
        return ([], 0)
    buckets: dict = {}
    buckets[_bucket_key(state0, target_slot)] = [(state0, [])]
    nodes = 0
    for _ in range(max_depth):
        new_buckets: dict = {}
        for key, cands in list(buckets.items()):
            for st, path in cands:
                for mv in MOVES:
                    nodes += 1
                    st2 = step(st, mv)
                    if _is_goal(st2, target_slot):
                        return (path + [mv], nodes)
                    k = _bucket_key(st2, target_slot)
                    new_buckets.setdefault(k, []).append((st2, path + [mv]))
        # 每桶截断 per_bucket；并按 (rel 高, co 桶小) 排序保留 max_buckets 桶
        for k in new_buckets:
            lst = new_buckets[k]
            lst.sort(key=lambda t: _score(t[0], target_slot))
            new_buckets[k] = lst[:per_bucket]
        ordered = sorted(new_buckets.items(), key=lambda kv: (-kv[0][0], kv[0][1]))
        buckets = dict(ordered[:max_buckets])
        if not buckets:
            return (None, nodes)
    return (None, nodes)


def _score(st: CompactPairingState, target_slot: str) -> Tuple[int, int, int]:
    rel = edge_relation(st, target_slot).relation
    co = color_off(st)
    return (rel, -co, 0)


def pair_one_edge_joint(
    cube: Cube5,
    target_slot: str,
    max_depth: int = 8,
    per_bucket: int = 16,
    max_buckets: int = 64,
) -> JointResult:
    """在真实 cube 基础上，联合搜索聚拢目标三块并把中心恢复到 color_off==0。

    全程用紧凑态搜索，命中后重放真实 cube 校验。
    """
    st0 = state_of(cube)
    moves, nodes = joint_search(st0, target_slot, max_depth, per_bucket, max_buckets)
    if moves is None:
        return JointResult(False, (), "FRONTIER_EXHAUSTED", nodes, max_depth)
    w = cube.clone()
    for mv in moves:
        w.apply_move(mv)
    ws = state_of(w)
    rel = edge_relation(ws, target_slot).relation
    paired = rel == GOAL_REL
    co = color_off(ws)
    ok = paired and co == 0
    return JointResult(ok, tuple(moves), None if ok else "REPLAY_MISMATCH", nodes, len(moves))
