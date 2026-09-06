"""中心闭环宏挖掘（plan §3.7）。

宏的验收条件（新）：起点中心颜色归面（co==0）、终点中心颜色归面（co==0）、
中间可任意扰动中心，且对目标棱产生有利变化（关系等级提升）。

本模块：从给定的（真实深打乱且中心已还原）紧凑状态出发，做「允许中心暂时扰动」
的谷式 beam 搜索，收集所有「终点 co==0 且 关系提升」的动作序列（中心闭环宏）。
这类宏成为自由切片装配的高层原子动作：套用它们时若起点中心归面、则终点中心归面，
从而在批量装配过程中**不积累**中心净扰动。

所有宏最终在真实 Cube5 上重放校验。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

from cube.cube5 import Cube5

from .compact_state import CompactPairingState, color_off, state_of, step
from .free_slice import edge_relation
from .compact_state import MOVES


@dataclass(frozen=True)
class ClosedMacro:
    moves: Tuple[str, ...]
    relation_before: int
    relation_after: int
    color_off_after: int
    length: int


def find_center_closed_improving(
    state0: CompactPairingState,
    target_slot: str,
    max_depth: int = 4,
    per_bucket: int = 24,
    max_buckets: int = 128,
    min_improve: int = 1,
) -> List[ClosedMacro]:
    """从 state0（要求中心已归面）出发，收集中心闭环且关系提升的宏。

    返回按 (relationship_after, -length) 排序的去重宏列表。
    """
    rel0 = edge_relation(state0, target_slot).relation
    found: Dict[Tuple[str, ...], ClosedMacro] = {}

    # bucket: (rel, co_bucket)
    def bucket(st):
        rel = edge_relation(st, target_slot).relation
        co = color_off(st)
        cb = 0 if co <= 4 else (1 if co <= 16 else 2)
        return (rel, cb)

    buckets: Dict = {bucket(state0): [(state0, ())]}
    for _ in range(max_depth):
        new_buckets: Dict = {}
        for key, cands in list(buckets.items()):
            for st, path in cands:
                for mv in MOVES:
                    st2 = step(st, mv)
                    path2 = path + (mv,)
                    rel2 = edge_relation(st2, target_slot).relation
                    co2 = color_off(st2)
                    if co2 == 0 and rel2 > rel0:
                        found.setdefault(path2, ClosedMacro(path2, rel0, rel2, co2, len(path2)))
                    k = bucket(st2)
                    new_buckets.setdefault(k, []).append((st2, path2))
        for k in new_buckets:
            lst = new_buckets[k]
            lst.sort(key=lambda t: (edge_relation(t[0], target_slot).relation, -color_off(t[0])))
            new_buckets[k] = lst[:per_bucket]
        ordered = sorted(new_buckets.items(), key=lambda kv: (-kv[0][0], kv[0][1]))
        buckets = dict(ordered[:max_buckets])
        if not buckets:
            break

    out = list(found.values())
    out.sort(key=lambda m: (m.relation_after, -m.length))
    return out


def discover_closed_macros_on_detail(
    work: Cube5,
    target_slot: str,
    max_depth: int = 4,
    per_bucket: int = 24,
    max_buckets: int = 128,
) -> List[ClosedMacro]:
    """在真实 cube 的紧凑态上挖中心闭环宏，并用真实 cube 重放复验。

    只返回「真实重放后 co==0 且关系>=rel0+min_improve」的宏。
    """
    st0 = state_of(work)
    macros = find_center_closed_improving(
        st0, target_slot, max_depth, per_bucket, max_buckets
    )
    out = []
    for m in macros:
        w = work.clone()
        for mv in m.moves:
            w.apply_move(mv)
        rel = edge_relation(state_of(w), target_slot).relation
        co = color_off(state_of(w))
        if co == 0 and rel >= m.relation_after:
            out.append(ClosedMacro(m.moves, m.relation_before, rel, co, len(m.moves)))
    return out
