"""单条棱构造原型（Milestone 2）：在固定工作槽中装配一条指定色对的逻辑棱。

模型：把 5x5 棱子系统（36 棱）与中心子系统（54 单贴面块）用「位置 -> 所在块 home」
的置换表示，配合预计算动作置换表，在搜索中避免整立方体克隆、只对目标评分。

搜索：受限 beam，评分优先把目标色对的 1 中 + 2 翼送入工作槽，同时抑制中心紊乱、
偏好短序列。达成的解必须满足：工作槽 is_edge_paired、中心全部还原、六个固定面心
原位、全部动作合法、从原状态重放一致。

说明（研究原型）：
- 本轮只要求「单条棱构造」，暂不要求保护其它已配棱（Milestone 3 再做）。
- 对受控/短打乱可成功；对深入打乱可能超出节点预算，返回 error_code 不假装成功。
"""

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

from cube.cube5 import Cube5

from .positions import (
    MIDDLE_INDEX,
    MIDDLE_ORDER,
    SLOT_NAMES,
    WING_INDEX,
    WING_ORDER,
    color_pair_of_slot,
    edge_type_of_cubie,
    slot,
)
from .moves import build_edge_move_effect

# 失败错误码
TARGET_ALREADY_SOLVED = "TARGET_ALREADY_SOLVED"
TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
SEARCH_BUDGET_EXHAUSTED = "SEARCH_BUDGET_EXHAUSTED"
SEARCH_DEAD_END = "SEARCH_DEAD_END"
SEARCH_LIMIT_REACHED = "SEARCH_LIMIT_REACHED"
SINGLE_EDGE_PAIR_ERRORS = (
    TARGET_ALREADY_SOLVED,
    TARGET_NOT_FOUND,
    SEARCH_BUDGET_EXHAUSTED,
    SEARCH_DEAD_END,
    SEARCH_LIMIT_REACHED,
)


@dataclass(frozen=True)
class SingleEdgePairResult:
    """单条棱构造结果与诊断。"""

    success: bool
    target: FrozenSet[str]
    work_slot: str
    moves: Tuple[str, ...]
    centers_restored: bool
    target_paired: bool
    error_code: Optional[str] = None
    message: str = ""
    nodes_explored: int = 0


# 中心位置与编号（贴 1 面）
_CENTERS = tuple(sorted(
    p for p, c in Cube5.solved().cubies.items() if len(c.stickers) == 1
))
_CENTER_INDEX: Dict[tuple, int] = {p: i for i, p in enumerate(_CENTERS)}
_N_CENTER = len(_CENTERS)

# 每个槽的「home 成员」对应的中/翼下标。
_SLOT_MID = {name: MIDDLE_INDEX[slot(name).middle] for name in SLOT_NAMES}
_SLOT_WINGS = {
    name: (WING_INDEX[slot(name).left_wing], WING_INDEX[slot(name).right_wing])
    for name in SLOT_NAMES
}
# 槽名 -> 其三个 home 成员对应的工作槽绝对坐标（用于判断入槽）。
_SLOT_POS = {name: (slot(name).middle, slot(name).left_wing, slot(name).right_wing)
             for name in SLOT_NAMES}
# 坐标 -> 所属「home 槽名」（用于判断某位置是否属于某槽）。
_POS_HOME_SLOT = {}
for name in SLOT_NAMES:
    for p in _SLOT_POS[name]:
        _POS_HOME_SLOT[p] = name
# 中/翼下标 -> 该下标当前 home 位置坐标
_MID_HOME = {i: p for i, p in enumerate(MIDDLE_ORDER)}
_WING_HOME = {i: p for i, p in enumerate(WING_ORDER)}


def _make_move_tables() -> Dict[str, Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]]:
    """每个动作的中/翼/中心三种位置置换表。"""
    tables = {}
    from solver.center5.legal_moves import LEGAL_5X5_CENTER_MOVES
    for mv in LEGAL_5X5_CENTER_MOVES:
        c = Cube5.solved()
        c.apply_move(mv)
        mid = tuple(MIDDLE_INDEX[c.cubies[p].home] for p in MIDDLE_ORDER)
        wing = tuple(WING_INDEX[c.cubies[p].home] for p in WING_ORDER)
        cen = tuple(_CENTER_INDEX[c.cubies[p].home] for p in _CENTERS)
        tables[mv] = (mid, wing, cen)
    return tables


_MOVE_TABLES = _make_move_tables()
_MOVES = tuple(_MOVE_TABLES.keys())


def _apply_mid(state, perm):
    return tuple(state[perm[j]] for j in range(len(state)))


def _apply_wing(state, perm):
    return tuple(state[perm[j]] for j in range(len(state)))


def _apply_center(state, perm):
    return tuple(state[perm[j]] for j in range(len(state)))


def _state_of(cube: Cube5) -> Tuple[tuple, tuple, tuple]:
    """读取当前立方体的中/翼/中心位置置换。"""
    mid = tuple(MIDDLE_INDEX[cube.cubies[p].home] for p in MIDDLE_ORDER)
    wing = tuple(WING_INDEX[cube.cubies[p].home] for p in WING_ORDER)
    cen = tuple(_CENTER_INDEX[cube.cubies[p].home] for p in _CENTERS)
    return mid, wing, cen


def _step(state, mv) -> Tuple[tuple, tuple, tuple]:
    mid, wing, cen = state
    pm, pw, pc = _MOVE_TABLES[mv]
    return (_apply_mid(mid, pm), _apply_wing(wing, pw), _apply_center(cen, pc))


# 每个中心位置所属的面（用于按颜色而非按身份统计中心错位）。
from .state import face_of_position
_CENTER_FACE = tuple(face_of_position(p) for p in _CENTERS)
# 面 -> 颜色（由固定面心读出；固定面心对合法动作恒定，故可预计算）。
from .state import face_colors
_solved_5x5 = Cube5.solved()
_face_to_color = face_colors(_solved_5x5)
_CENTER_COLOR = tuple(_face_to_color[_CENTER_FACE[i]] for i in range(_N_CENTER))


def _color_off(state) -> int:
    """中心「按颜色归面」的错位数（外层动作不影响，宽层动作跨面色才计）。

    位置 j 上坐着「home 为 _CENTERS[v]」的块；其颜色为其 home 面的颜色。
    若该颜色 != 位置 j 所在面的颜色，计 1。
    """
    mid, wing, cen = state
    return sum(1 for j, v in enumerate(cen) if _CENTER_COLOR[v] != _CENTER_COLOR[j])


def _center_off(state) -> int:
    mid, wing, cen = state
    return sum(1 for j, v in enumerate(cen) if v != j)


def _matched(state, target_home_slot: str, work_slot: str) -> int:
    """工作槽中属于目标色对的成员数。"""
    mid, wing, cen = state
    work_pos = set(_SLOT_POS[work_slot])
    # 目标成员：其 home 属于 target_home_slot 的 3 个块的下标
    tmid = _SLOT_MID[target_home_slot]
    tw1, tw2 = _SLOT_WINGS[target_home_slot]
    cnt = 0
    # 找这些块的当前坐标
    # 目标中块当前坐标：在 mid 中，当前位置 j 的值为 tmid
    for j, v in enumerate(mid):
        if v == tmid and MIDDLE_ORDER[j] in work_pos:
            cnt += 1
    for j, v in enumerate(wing):
        if v in (tw1, tw2) and WING_ORDER[j] in work_pos:
            cnt += 1
    return cnt


def _work_paired(state, work_slot: str) -> bool:
    """工作槽 3 个位置是否容纳了同一 home 槽（同一色对）的 3 个成员。"""
    mid, wing, cen = state
    mpos = slot(work_slot).middle
    lwpos = slot(work_slot).left_wing
    rwpos = slot(work_slot).right_wing
    hs = set()
    for pos in (mpos, lwpos, rwpos):
        if pos in MIDDLE_INDEX:
            j = MIDDLE_INDEX[pos]
            v = mid[j]
            hs.add(_POS_HOME_SLOT[MIDDLE_ORDER[v]])
        else:
            j = WING_INDEX[pos]
            v = wing[j]
            hs.add(_POS_HOME_SLOT[WING_ORDER[v]])
    return len(hs) == 1


def _score_state(matched: int, color_off: int, depth: int) -> int:
    """优先把目标成员送入工作槽，同时抑制中心「按颜色归面」错位，并偏好短序列。

    目标须同时 matched==3 且 color_off==0；外层动作不产生 color_off，故评分框架
    只惩罚真正破坏面色（宽层跨面）的路径。达成由显式检查（color_off==0 且 work_paired）保证。
    """
    return matched * 1000 - color_off * 1 - depth


def _target_home_slot(cube: Cube5, target: FrozenSet[str]) -> Optional[str]:
    """返回色对 == target 所对应的 home 逻辑槽名。"""
    for name in SLOT_NAMES:
        if color_pair_of_slot(name, _face_colors_of(cube)) == target:
            return name
    return None


def _face_colors_of(cube: Cube5) -> Dict[str, str]:
    from .state import face_colors
    return face_colors(cube)


def pair_single_edge(
    cube: Cube5,
    target: FrozenSet[str],
    work_slot: str,
    max_depth: int = 24,
    beam_width: int = 300,
    node_budget: int = 2000000,
) -> SingleEdgePairResult:
    """在固定工作槽中装配 target 色对的逻辑棱，且最终中心还原。

    不修改输入 cube；返回结果含动作序列与诊断。若失败给出 error_code。
    """
    original = cube.clone()
    if work_slot not in SLOT_NAMES:
        raise ValueError("未知工作槽: %s" % work_slot)

    from .state import is_edge_paired as _iep
    from .state import centers_are_color_solved as _centers_solved_color

    def _all_centers_solved(cube):
        # 目标：中心按颜色归面（同色中心块无需回到唯一 home 槽）。
        return _centers_solved_color(cube)

    def _fixed_centers_at_home(cube):
        for c in cube.cubies.values():
            if len(c.stickers) == 1 and sorted(abs(v) for v in c.home) == [0, 0, 6]:
                if c.pos != c.home:
                    return False
        return True

    tgt_home = _target_home_slot(original, target)
    if tgt_home is None:
        return SingleEdgePairResult(
            success=False, target=target, work_slot=work_slot, moves=(),
            centers_restored=False, target_paired=False,
            error_code=TARGET_NOT_FOUND, message="无法确定目标色对对应的 home 槽",
            nodes_explored=0,
        )
    if _iep(original, work_slot) and _all_centers_solved(cube):
        return SingleEdgePairResult(
            success=True, target=target, work_slot=work_slot, moves=(),
            centers_restored=True, target_paired=True, nodes_explored=0,
            message="已满足",
        )

    start = _state_of(original)
    beam: List[Tuple[Tuple[tuple, tuple, tuple], List[str]]] = [(start, [])]
    nodes = 0
    exit_reason = None

    for _depth in range(max_depth):
        scored = []
        for st, path in beam:
            m = _matched(st, tgt_home, work_slot)
            co = _color_off(st)
            scored.append((_score_state(m, co, len(path)), st, path))
            # 若已达成，尝试做最终校验
        # 检查当前 beam 是否有满足解
        for _s, st, path in scored:
            if _matched(st, tgt_home, work_slot) == 3 and _color_off(st) == 0 \
                    and _work_paired(st, work_slot):
                replay = original.clone()
                replay.apply_moves(path)
                if _iep(replay, work_slot) and _all_centers_solved(replay) \
                        and _fixed_centers_at_home(replay):
                    return SingleEdgePairResult(
                        success=True, target=target, work_slot=work_slot,
                        moves=tuple(path), centers_restored=True,
                        target_paired=True, nodes_explored=nodes,
                        message="装配成功",
                    )
        nxt = []
        for _s, st, path in scored:
            for mv in _MOVES:
                nodes += 1
                if nodes > node_budget:
                    break
                ns = _step(st, mv)
                m = _matched(ns, tgt_home, work_slot)
                co = _color_off(ns)
                np = path + [mv]
                if m == 3 and co == 0 and _work_paired(ns, work_slot):
                    replay = original.clone()
                    replay.apply_moves(np)
                    if _iep(replay, work_slot) and _all_centers_solved(replay) \
                            and _fixed_centers_at_home(replay):
                        return SingleEdgePairResult(
                            success=True, target=target, work_slot=work_slot,
                            moves=tuple(np), centers_restored=True,
                            target_paired=True, nodes_explored=nodes, message="装配成功",
                        )
                nxt.append((_score_state(m, co, len(np)), ns, np))
            if nodes > node_budget:
                exit_reason = SEARCH_BUDGET_EXHAUSTED
                break
        if nodes > node_budget:
            exit_reason = SEARCH_BUDGET_EXHAUSTED
            break
        # 去重 + 排序取 beam_width
        seen = {}
        for score, st, path in nxt:
            key = (st[0], st[1], st[2])
            if key in seen and seen[key][0] >= score:
                continue
            seen[key] = (score, st, path)
        pool = sorted(seen.items(), key=lambda kv: kv[1][0], reverse=True)
        beam = [(item[1][1], item[1][2]) for item in pool[:beam_width]]
        if not beam:
            exit_reason = SEARCH_DEAD_END
            break

    return SingleEdgePairResult(
        success=False, target=target, work_slot=work_slot, moves=(),
        centers_restored=False, target_paired=False,
        error_code=exit_reason or SEARCH_LIMIT_REACHED,
        message="未找到满足条件的序列 (%s)" % (exit_reason or SEARCH_LIMIT_REACHED),
        nodes_explored=nodes,
    )
