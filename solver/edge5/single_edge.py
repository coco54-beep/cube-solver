"""单棱构造器正式实现（Milestone 2.5）：穿谷分桶 beam。

目标（单一联合目标，允许中途退回）：

    is_edge_paired(cube, target) and centers_are_color_solved(cube)

搜索过程允许：
  - 目标三块聚集后再次拆散；
  - 中心错位暂时增加；
  - 匹配数从 3 退回 2/1/0；
  - 未保护棱任意变化。

核心手段：分桶 beam。每层候选按
  (目标匹配成员数, 中心颜色错位档, 穿谷深度档)
独立保留，避免「目标已聚集但中心无法恢复」的状态占满 beam，从而保留跨越
临时山谷（先降匹配/升错位、后恢复）的路线。

与 M2 的关系：M2 的 pair_single_edge 使用单调评分，仅适合受控/短打乱；
本模块以「允许穿谷」为目标，用于深打乱。两者并存，本模块不修改 M2。
"""

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

from cube.cube5 import Cube5

from .compact_state import (
    MOVES,
    CompactPairingState,
    bucket_key,
    color_off,
    matched,
    score_state,
    state_of,
    step,
    target_home_slot,
    work_paired,
)
from .positions import slot as _slot

# 失败错误码
TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
NODE_LIMIT = "SEARCH_NODE_LIMIT"
DEPTH_LIMIT = "SEARCH_DEPTH_LIMIT"
TIME_LIMIT = "SEARCH_TIME_LIMIT"
FRONTIER_EXHAUSTED = "SEARCH_FRONTIER_EXHAUSTED"
ABSTRACTION_REPLAY_MISMATCH = "ABSTRACTION_REPLAY_MISMATCH"
SINGLE_EDGE_VALLEY_ERRORS = (
    NODE_LIMIT,
    DEPTH_LIMIT,
    TIME_LIMIT,
    FRONTIER_EXHAUSTED,
    ABSTRACTION_REPLAY_MISMATCH,
)


@dataclass(frozen=True)
class SearchLimits:
    """所有搜索接口统一支持的资源上限。"""

    max_nodes: int = 10_000_000
    max_depth: int = 50
    timeout_seconds: float = 45.0
    beam_width: int = 2000
    per_bucket: int = 80
    bucket_cap: int = 6


@dataclass(frozen=True)
class ValleySingleEdgeResult:
    """单棱构造（穿谷版）结果与诊断。"""

    success: bool
    target: FrozenSet[str]
    work_slot: str
    moves: Tuple[str, ...]
    centers_restored: bool
    target_paired: bool
    error_code: Optional[str] = None
    message: str = ""
    nodes_explored: int = 0


# ---------------------------------------------------------------------------
# 禁忌 / 动作剪枝（只做安全剪枝）
# ---------------------------------------------------------------------------

def _face_letter(mv: str) -> str:
    s = mv.lstrip("0123456789")
    return s[0]


def _layers(mv: str) -> int:
    i = 0
    while i < len(mv) and mv[i].isdigit():
        i += 1
    prefix = mv[:i]
    return int(prefix) if prefix else 1


def _count(mv: str) -> int:
    if mv.endswith("''"):
        return 2
    if mv.endswith("'"):
        return 3
    if mv.endswith("2"):
        return 2
    if mv.endswith("3"):
        return 3
    return 1


def _same_basis(a: str, b: str) -> bool:
    return _layers(a) == _layers(b) and _face_letter(a) == _face_letter(b)


def _is_inverse(a: str, b: str) -> bool:
    return _same_basis(a, b) and (_count(a) + _count(b)) % 4 == 0


def _legal_next(prev_moves: List[str], mv: str) -> bool:
    """是否允许把 mv 追加到 prev_moves 之后（只做安全剪枝）。"""
    if not prev_moves:
        return True
    last = prev_moves[-1]
    # 禁止动作后立即执行其逆。
    if _is_inverse(last, mv):
        return False
    # 四次同动作循环不展开。
    if len(prev_moves) >= 4:
        if all(m == last for m in prev_moves[-3:]):
            return False
    return True


# ---------------------------------------------------------------------------
# 目标校验
# ---------------------------------------------------------------------------

def _edge_type_in_slot(cube: Cube5, work_slot: str):
    """返回工作槽中整条棱的色对（须 is_edge_paired），否则 None。"""
    from .state import edge_type_at

    s = _slot(work_slot)
    return edge_type_at(cube, s.middle)


def _fixed_centers_at_home(cube: Cube5) -> bool:
    for c in cube.cubies.values():
        if len(c.stickers) == 1 and sorted(abs(v) for v in c.home) == [0, 0, 6]:
            if c.pos != c.home:
                return False
    return True


# beam 元素：状态、路径、目标成员数、中心错位、历史最优 (matched, -color_off)、穿谷深度
_BeamItem = Tuple[CompactPairingState, List[str], int, int, Tuple[int, int], int]


def _mk(st, path, m, co, best, valley):
    return (st, path, m, co, best, valley)


def _item_score(it: _BeamItem) -> tuple:
    st, path, m, co, best, valley = it
    return score_state(m, co, valley, len(path))


def _select_bucketed(nxt: List[_BeamItem], limits: SearchLimits) -> List[_BeamItem]:
    """把候选按桶分组，每桶保留 top 若干，再按总分排序取 beam_width。"""
    buckets: Dict[Tuple[int, int, int], List[_BeamItem]] = {}
    for item in nxt:
        st, path, m, co, best, valley = item
        key = bucket_key(m, co, valley)
        buckets.setdefault(key, []).append(item)
    picked: List[_BeamItem] = []
    for items in buckets.values():
        scored = sorted(items, key=_item_score, reverse=True)
        picked.extend(scored[:limits.per_bucket])
    picked.sort(key=_item_score, reverse=True)
    seen = set()
    result = []
    for it in picked:
        key = it[0].key
        if key in seen:
            continue
        seen.add(key)
        result.append(it)
        if len(result) >= limits.beam_width:
            break
    return result


def pair_single_edge_valley(
    cube: Cube5,
    target: FrozenSet[str],
    work_slot: str,
    limits: Optional[SearchLimits] = None,
) -> ValleySingleEdgeResult:
    """在固定工作槽装配 target 色对逻辑棱，最终中心按颜色归面。

    使用允许穿谷的分桶 beam。不修改输入 cube；返回动作序列与诊断。
    失败返回结构化 error_code，不假装成功。
    """
    import time as _time

    limits = limits or SearchLimits()
    original = cube.clone()

    from .state import centers_are_color_solved, is_edge_paired

    def _all_centers_solved(c):
        return centers_are_color_solved(c)

    tgt_home = target_home_slot(original, target)
    if tgt_home is None:
        return ValleySingleEdgeResult(
            success=False, target=target, work_slot=work_slot, moves=(),
            centers_restored=False, target_paired=False,
            error_code=TARGET_NOT_FOUND, message="无法确定目标色对对应的 home 槽",
        )

    if is_edge_paired(original, work_slot) and _all_centers_solved(original):
        if _edge_type_in_slot(original, work_slot) == target:
            return ValleySingleEdgeResult(
                success=True, target=target, work_slot=work_slot, moves=(),
                centers_restored=True, target_paired=True,
                message="已满足目标", nodes_explored=0,
            )

    start = state_of(original)
    m0 = matched(start, tgt_home, work_slot)
    co0 = color_off(start)
    beam: List[_BeamItem] = [_mk(start, [], m0, co0, (m0, -co0), 0)]
    nodes = 0
    start_time = _time.monotonic()
    exit_reason = None

    def _verify(path_moves: List[str]) -> Optional[ValleySingleEdgeResult]:
        replay = original.clone()
        replay.apply_moves(path_moves)
        if (is_edge_paired(replay, work_slot) and _all_centers_solved(replay)
                and _fixed_centers_at_home(replay)
                and _edge_type_in_slot(replay, work_slot) == target):
            return ValleySingleEdgeResult(
                success=True, target=target, work_slot=work_slot,
                moves=tuple(path_moves), centers_restored=True,
                target_paired=True, nodes_explored=nodes, message="装配成功",
            )
        return None

    for depth in range(limits.max_depth):
        for st, path, m, co, _best, _v in beam:
            if m == 3 and co == 0 and work_paired(st, work_slot):
                res = _verify(path)
                if res is not None:
                    return res
        nxt: List[_BeamItem] = []
        for st, path, _m, _co, best, valley in beam:
            for mv in MOVES:
                nodes += 1
                if nodes > limits.max_nodes:
                    exit_reason = NODE_LIMIT
                    break
                if not _legal_next(path, mv):
                    continue
                ns = step(st, mv)
                m = matched(ns, tgt_home, work_slot)
                co = color_off(ns)
                obj = (m, -co)
                if obj > best:
                    new_best = obj
                    new_valley = 0
                else:
                    new_best = best
                    new_valley = valley + 1
                np = path + [mv]
                nxt.append(_mk(ns, np, m, co, new_best, new_valley))
                if m == 3 and co == 0 and work_paired(ns, work_slot):
                    res = _verify(np)
                    if res is not None:
                        return res
            if nodes > limits.max_nodes:
                break
        if nodes > limits.max_nodes:
            break
        if _time.monotonic() - start_time > limits.timeout_seconds:
            exit_reason = TIME_LIMIT
            break
        if not nxt:
            exit_reason = FRONTIER_EXHAUSTED
            break
        beam = _select_bucketed(nxt, limits)
        if not beam:
            exit_reason = FRONTIER_EXHAUSTED
            break

    return ValleySingleEdgeResult(
        success=False, target=target, work_slot=work_slot, moves=(),
        centers_restored=False, target_paired=False,
        error_code=exit_reason or DEPTH_LIMIT,
        message="未找到满足条件的序列 (%s)" % (exit_reason or DEPTH_LIMIT),
        nodes_explored=nodes,
    )
