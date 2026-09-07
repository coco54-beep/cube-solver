"""确定性 free-slice 单条三块棱完整装配（Gate 5）。

Gate 5 目标：给定一个「中棱 + 翼-A」的 rel>=2 部分组合（通常已存到安全槽，
或已与该中棱同槽）以及一条松散的「翼-B」，把三者装配成**完整一条三块棱**，
产出 `is_edge_paired(after, output_slot) == True` 且三块同槽住。

核心机制（Gate 2-4 实证）：
- 纯外层 1X 是纯位置置换，会把与中棱同槽的翼一起带走（同槽不变）。故「联合定位」
  （joint setup）只须在 (中棱位置, 翼-B位置) 状态空间上用纯外层 BFS，把部分组合的中棱
  送入目标 `partial_slot`、把翼-B 送入目标入口翼位（wing_entry）。
- 随后执行 free-slice 本体 `2F + outer + 2F'`，把翼-B 装配进中棱所在槽（含翼-A）。
- 若本体后三块同槽但未朝向一致，用中心保持宏做 flip-fix（见 `_flip_fix`）。

多目标：`completion_goal_states` 枚举多个合法输出槽（工作槽 UF 与安全槽
BL/BR/DB/UB）及多种翼入口位置，避免单一固定目标过窄（解决 seed 5 类「中棱已在安全槽」
与部分不可达问题）。

正确性约束（均真实 Cube5 重放校验，见各后置）：
- 只用物理合法动作（1X + 2X；绝不 3X/4X/5X，它们会移动固定面心）。
- 定位 setup 只用纯外层 1X；free-slice 用 2F + outer + 2F'（开/关切片后中心恢复归面）。
- 本模块只读，不修改传入 cube。

错误码见各常量。`PartialRelation` 描述部分组合/完整棱的状态分级。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .compact_state import MOVE_TABLES
from .freeslice_layout import FreeSliceLayout, DEFAULT_LAYOUT, OUTER_MOVES
from .positions import (
    MIDDLE_ORDER, WING_ORDER, SLOT_NAMES, slot, slot_of, MIDDLE_INDEX, WING_INDEX,
    edge_type_of_cubie,
)
from .state import centers_are_color_solved, is_edge_paired
from .free_slice import _fixed_centers_preserved
from .atomic_insert import middle_wing_relation_real, REL_COMBO, REL_ORIENTED

# free-slice 本体（open + outer + close）；outer 部分与 Gate 3 一致。
_INSERT_OUTER: Tuple[str, ...] = ("U", "F'", "U'")

# 候选部分组合所在槽（工作槽 + 4 个 safe-untouched 存储槽优先，再覆盖全部逻辑槽）。
# 完整装配可能在某些「非工作/非存储」槽才收敛（如 seed 11 只能在 UL 配齐），
# 故覆盖全部 SLOT_NAMES；前面优先尝试规范槽，保证既有 seed 3/6/21 行为不变。
_DEFAULT_PARTIAL_SLOTS: Tuple[str, ...] = (
    "UF", "BL", "BR", "DB", "UB",
    "UR", "UL", "DF", "DR", "DL", "FR", "FL",
)

CENTER_NOT_RESTORED = "CENTER_NOT_RESTORED"
FIXED_CENTER_MOVED = "FIXED_CENTER_MOVED"
REPLAY_MISMATCH = "REPLAY_MISMATCH"
PARTIAL_NOT_RECOVERABLE = "PARTIAL_NOT_RECOVERABLE"
COMPLETION_SETUP_UNREACHABLE = "COMPLETION_SETUP_UNREACHABLE"
SECOND_INSERT_SCATTERED = "SECOND_INSERT_SCATTERED"
POSITIONAL_TREDGE_NOT_FORMED = "POSITIONAL_TREDGE_NOT_FORMED"
FLIP_FIX_UNAVAILABLE = "FLIP_FIX_UNAVAILABLE"
FLIP_FIX_FAILED = "FLIP_FIX_FAILED"
PRECONDITION_FAILED = "PRECONDITION_FAILED"
NO_GOAL_COMPLETED = "NO_GOAL_COMPLETED"


class PartialRelation(Enum):
    """部分组合 / 完整棱的状态分级（按 Gate 5 语义）。"""

    STORED_TOGETHER = "stored_together"      # 中棱+翼-A 同槽且色对一致（rel>=2）
    RECOVERABLE = "recoverable"              # 可被纯外层整体搬回工作带
    SCATTERED = "scattered"                  # 三块不同槽
    POSITIONAL_TREDGE = "positional_tredge"  # 三块同槽但未朝向一致
    VALID_TREDGE = "valid_tredge"            # 三块同槽且 is_edge_paired（完整正确）


@dataclass(frozen=True)
class TredgeCompletionState:
    """一条目标棱在校验点上的装配状态描述。"""

    partial_relation: PartialRelation
    middle_slot: Optional[str]
    wing_a_slot: Optional[str]
    wing_b_slot: Optional[str]
    relation_a_level: int
    relation_b_level: int
    centers_solved: bool
    fixed_centers_preserved: bool
    output_slot: Optional[str] = None

    @property
    def all_three_together(self) -> bool:
        return (self.middle_slot is not None
                and self.middle_slot == self.wing_a_slot
                and self.middle_slot == self.wing_b_slot)

    @property
    def is_valid(self) -> bool:
        return self.partial_relation is PartialRelation.VALID_TREDGE


@dataclass(frozen=True)
class CompletionGoal:
    """一个完整装配目标：把部分组合送入 partial_slot、翼-B 送入 wing_entry，再跑本体。"""

    partial_slot: str
    wing_entry_pos: int
    open_move: str
    insert_outer: Tuple[str, ...]
    close_move: str

    @property
    def body(self) -> Tuple[str, ...]:
        return (self.open_move,) + self.insert_outer + (self.close_move,)

    @property
    def description(self) -> str:
        return "partial=%s entry_pos=%d" % (self.partial_slot, self.wing_entry_pos)


def completion_goal_states(
    layout: Optional[FreeSliceLayout] = None,
    partial_slots: Tuple[str, ...] = _DEFAULT_PARTIAL_SLOTS,
) -> Tuple[CompletionGoal, ...]:
    """枚举候选装配目标（部分槽 × 翼入口位置），确定性排序。"""
    layout = layout or DEFAULT_LAYOUT
    goals: List[CompletionGoal] = []
    for ps in partial_slots:
        for we in range(len(WING_ORDER)):
            goals.append(CompletionGoal(
                partial_slot=ps,
                wing_entry_pos=we,
                open_move=layout.open_move,
                insert_outer=_INSERT_OUTER,
                close_move=layout.close_move,
            ))
    # 稳定：部分槽按给定顺序、入口按位置升序
    return tuple(goals)


def _invert_perm(perm: Tuple[int, ...]) -> Tuple[int, ...]:
    inv = [0] * len(perm)
    for i, v in enumerate(perm):
        inv[v] = i
    return tuple(inv)


# 纯外层前向置换（中/翼），与 freeslice_layout 一致。
_FWD = {mv: (_invert_perm(MOVE_TABLES[mv][0]), _invert_perm(MOVE_TABLES[mv][1]))
        for mv in OUTER_MOVES}

# (target_mid_pos, target_wing_pos) -> { (mid_pos, wing_pos): 前向序列 }
_JOINT_CACHE: Dict[Tuple[int, int], Dict[Tuple[int, int], Tuple[str, ...]]] = {}


def _joint_table(t_mid: int, t_wing: int, max_depth: int = 8) -> Dict[Tuple[int, int], Tuple[str, ...]]:
    """构建以 (t_mid, t_wing) 为目标的最短纯外层联合表（逆向 BFS，可缓存）。"""
    key = (t_mid, t_wing)
    cached = _JOINT_CACHE.get(key)
    if cached is not None:
        return cached
    inv_mid = {mv: _invert_perm(_FWD[mv][0]) for mv in OUTER_MOVES}
    inv_wing = {mv: _invert_perm(_FWD[mv][1]) for mv in OUTER_MOVES}
    target = (t_mid, t_wing)
    best = {target: ()}
    frontier = deque([target])
    while frontier:
        mpos, wpos = frontier.popleft()
        path = best[(mpos, wpos)]
        if len(path) >= max_depth:
            continue
        for mv in OUTER_MOVES:
            prev = (inv_mid[mv][mpos], inv_wing[mv][wpos])
            if prev in best:
                continue
            best[prev] = (mv,) + path
            frontier.append(prev)
    _JOINT_CACHE[key] = best
    return best


def _cubie_by_home(cube, home_coord):
    for pos, cubie in cube.cubies.items():
        if cubie.home == home_coord:
            return cubie
    return None


def _mid_pos(cube, middle_piece_id: int) -> Optional[int]:
    from .compact_state import state_of
    st = state_of(cube)
    return next((j for j, v in enumerate(st.middle) if v == middle_piece_id), None)


def _wing_pos(cube, wing_piece_id: int) -> Optional[int]:
    from .compact_state import state_of
    st = state_of(cube)
    return next((j for j, v in enumerate(st.wing) if v == wing_piece_id), None)


def find_partial_wing_setup(
    cube,
    middle_piece_id: int,
    wing_b_piece_id: int,
    goal: CompletionGoal,
) -> Optional[Tuple[str, ...]]:
    """纯外层联合 setup：把部分组合之中棱送入 goal.partial_slot、翼-B 送入 goal.wing_entry_pos。

    不改写 cube。若 (当前中棱位置, 当前翼-B位置) 不可达该目标，返回 None。
    """
    mpos = _mid_pos(cube, middle_piece_id)
    wpos = _wing_pos(cube, wing_b_piece_id)
    if mpos is None or wpos is None:
        return None
    t_mid = MIDDLE_INDEX[slot(goal.partial_slot).middle]
    tbl = _joint_table(t_mid, goal.wing_entry_pos)
    return tbl.get((mpos, wpos))


def describe_partial(
    cube,
    middle_piece_id: int,
    wing_a_piece_id: int,
    wing_b_piece_id: int,
) -> TredgeCompletionState:
    """描述当前 cube 上一条目标棱的装配状态。只读。"""
    ra = middle_wing_relation_real(cube, middle_piece_id, wing_a_piece_id)
    rb = middle_wing_relation_real(cube, middle_piece_id, wing_b_piece_id)
    mc = _cubie_by_home(cube, MIDDLE_ORDER[middle_piece_id])
    ac = _cubie_by_home(cube, WING_ORDER[wing_a_piece_id])
    bc = _cubie_by_home(cube, WING_ORDER[wing_b_piece_id])
    ms = slot_of(mc.pos) if mc else None
    as_ = slot_of(ac.pos) if ac else None
    bs = slot_of(bc.pos) if bc else None

    centers = centers_are_color_solved(cube)
    fixed = _fixed_centers_preserved(cube)

    # 判定完整棱状态
    out_slot = None
    if ms is not None and ms == as_ == bs:
        out_slot = ms
        if is_edge_paired(cube, ms):
            rel = PartialRelation.VALID_TREDGE
        else:
            rel = PartialRelation.POSITIONAL_TREDGE
    elif ra.relation_level >= REL_COMBO and ra.same_logical_slot:
        rel = PartialRelation.STORED_TOGETHER
    else:
        rel = PartialRelation.SCATTERED

    return TredgeCompletionState(
        partial_relation=rel,
        middle_slot=ms,
        wing_a_slot=as_,
        wing_b_slot=bs,
        relation_a_level=ra.relation_level,
        relation_b_level=rb.relation_level,
        centers_solved=centers,
        fixed_centers_preserved=fixed,
        output_slot=out_slot,
    )


def all_three_target_pieces_in_output_slot(cube, middle_piece_id, wing_a_piece_id, wing_b_piece_id, output_slot) -> bool:
    """三个目标 piece 是否都位于 output_slot。"""
    mc = _cubie_by_home(cube, MIDDLE_ORDER[middle_piece_id])
    ac = _cubie_by_home(cube, WING_ORDER[wing_a_piece_id])
    bc = _cubie_by_home(cube, WING_ORDER[wing_b_piece_id])
    if mc is None or ac is None or bc is None:
        return False
    return (slot_of(mc.pos) == output_slot
            and slot_of(ac.pos) == output_slot
            and slot_of(bc.pos) == output_slot)


def _full_state_fingerprint(cube) -> Tuple:
    return tuple(
        (p, cubie.home, tuple(sorted(cubie.stickers.items())))
        for p, cubie in sorted(cube.cubies.items())
    )


@dataclass
class CompleteTredgeResult:
    """Gate 5 完整装配结果。

    `goal` 为成功使用的装配目标；`flip_moves` 为 flip-fix 动作（可能为空）。
    `side_effects` 记录本次装配对其它已配对槽（保护组）的影响（Gate 6 输入）。
    `state_after` 为验收后的完整 Cube5。
    """

    success: bool
    moves: Tuple[str, ...]
    middle_piece_id: int
    wing_a_piece_id: int
    wing_b_piece_id: int
    output_slot: Optional[str]
    state_before: Optional[TredgeCompletionState]
    state_after: Optional[TredgeCompletionState]
    goal: Optional[CompletionGoal]
    setup_moves: Tuple[str, ...]
    insert_moves: Tuple[str, ...]
    flip_moves: Tuple[str, ...]
    side_effects: Dict[str, object]
    centers_solved_after: bool
    fixed_centers_preserved: bool
    replay_consistent: bool
    error_code: Optional[str]
    message: str = "ok"


def _protected_slots_affected(cube_before, cube_after) -> Dict[str, object]:
    """记录 `cube_after` 相比 `cube_before` 在「已配对槽」上的变化。

    对每个逻辑槽：拆散 / 兼容 / 新配 / 无关。门 6 输入由该报告驱动。
    """
    from .positions import SLOT_NAMES as _SN
    report = {"broken": [], "preserved": [], "newly_paired": [], "untouched": []}
    for name in _SN:
        before = is_edge_paired(cube_before, name)
        after = is_edge_paired(cube_after, name)
        if after and before:
            report["preserved"].append(name)
        elif after and not before:
            report["newly_paired"].append(name)
        elif before and not after:
            report["broken"].append(name)
        else:
            report["untouched"].append(name)
    return report


def _flip_fix(cube, output_slot, macro_index=None, max_len: int = 5):
    """三块已同槽但未朝向一致时，找一个中心保持宏把该槽配好。

    只在该槽三块同槽、`is_edge_paired` 为假时调用。不改写 cube；返回动作或 None。
    """
    if macro_index is None:
        from .macro_index import build_macro_index
        macro_index = build_macro_index(3)
    for e in macro_index.effects:
        if e.length > max_len:
            continue
        x = cube.clone()
        for mv in e.moves:
            x.apply_move(mv)
        if centers_are_color_solved(x) and is_edge_paired(x, output_slot):
            return e.moves
    return None


def complete_tredge(
    cube,
    *,
    middle_piece_id: int,
    wing_a_piece_id: int,
    wing_b_piece_id: int,
    layout: Optional[FreeSliceLayout] = None,
    try_flip: bool = True,
    macro_index=None,
) -> CompleteTredgeResult:
    """把「中棱 + 翼-A」部分组合与松散的翼-B 装配为完整一条三块棱。

    不改写输入 cube。成功条件：`is_edge_paired(after, output_slot)` 为真、
    三块同住 output_slot、中心归面、固定面心保持、真实重放一致。

    失败时返回对应 error_code（各错误码见模块内常量）。
    """
    layout = layout or DEFAULT_LAYOUT

    def fail(code, msg, **kw):
        return CompleteTredgeResult(
            success=False, moves=(), middle_piece_id=middle_piece_id,
            wing_a_piece_id=wing_a_piece_id, wing_b_piece_id=wing_b_piece_id,
            output_slot=kw.get("output_slot"),
            state_before=kw.get("state_before"), state_after=kw.get("state_after"),
            goal=kw.get("goal"), setup_moves=kw.get("setup_moves", ()),
            insert_moves=kw.get("insert_moves", ()), flip_moves=kw.get("flip_moves", ()),
            side_effects=kw.get("side_effects", {}),
            centers_solved_after=kw.get("centers_solved_after", False),
            fixed_centers_preserved=kw.get("fixed_centers_preserved", False),
            replay_consistent=kw.get("replay_consistent", False),
            error_code=code, message=msg,
        )

    # 前置
    state_before = describe_partial(cube, middle_piece_id, wing_a_piece_id, wing_b_piece_id)
    if not state_before.centers_solved:
        return fail(PRECONDITION_FAILED, "中心未归面", state_before=state_before)
    if not state_before.fixed_centers_preserved:
        return fail(PRECONDITION_FAILED, "固定面心已被移动", state_before=state_before)

    # 快路径：已经是完整可用的三块棱（含已在某槽配好）
    if state_before.partial_relation is PartialRelation.VALID_TREDGE:
        out = state_before.output_slot
        return CompleteTredgeResult(
            success=True, moves=(), middle_piece_id=middle_piece_id,
            wing_a_piece_id=wing_a_piece_id, wing_b_piece_id=wing_b_piece_id,
            output_slot=out, state_before=state_before, state_after=state_before,
            goal=None, setup_moves=(), insert_moves=(), flip_moves=(),
            side_effects=_protected_slots_affected(cube, cube),
            centers_solved_after=True, fixed_centers_preserved=True,
            replay_consistent=True, error_code=None, message="already valid",
        )
    if state_before.partial_relation is not PartialRelation.STORED_TOGETHER:
        return fail(PARTIAL_NOT_RECOVERABLE,
                    "部分组合未形成中棱+翼-A 同槽 rel>=2 组合（不可整体搬运）",
                    state_before=state_before)

    goals = completion_goal_states(layout)

    for goal in goals:
        setup = find_partial_wing_setup(cube, middle_piece_id, wing_b_piece_id, goal)
        if setup is None:
            continue
        w = cube.clone()
        setup_moves = tuple(setup)
        for mv in setup_moves:
            w.apply_move(mv)
        insert_moves = goal.body
        for mv in insert_moves:
            w.apply_move(mv)

        # 检查中心/固定面心（粉末分布可能未恢复，允许 flip-fix 后再复查）
        state_mid = describe_partial(w, middle_piece_id, wing_a_piece_id, wing_b_piece_id)

        if state_mid.all_three_together:
            out_slot = state_mid.middle_slot
            flip_moves: Tuple[str, ...] = ()
            w2 = w.clone()
            if not is_edge_paired(w2, out_slot):
                if not try_flip:
                    return fail(POSITIONAL_TREDGE_NOT_FORMED,
                                "三块已同槽但 flip-fix 被禁用/不可用",
                                output_slot=out_slot, state_before=state_before,
                                state_after=state_mid, goal=goal,
                                setup_moves=setup_moves, insert_moves=insert_moves)
                fx = _flip_fix(w2, out_slot, macro_index)
                if fx is None:
                    return fail(FLIP_FIX_UNAVAILABLE, "三块同槽但无法翻转成配对",
                                output_slot=out_slot, state_before=state_before,
                                state_after=state_mid, goal=goal,
                                setup_moves=setup_moves, insert_moves=insert_moves)
                flip_moves = tuple(fx)
                for mv in flip_moves:
                    w2.apply_move(mv)
                state_mid = describe_partial(w2, middle_piece_id, wing_a_piece_id, wing_b_piece_id)

            after = state_mid
            final_success = (
                after.partial_relation is PartialRelation.VALID_TREDGE
                and after.centers_solved
                and after.fixed_centers_preserved
                and after.output_slot is not None
            )
            all_moves = setup_moves + insert_moves + flip_moves
            replay = cube.clone()
            for mv in all_moves:
                replay.apply_move(mv)
            replay_ok = _full_state_fingerprint(replay) == _full_state_fingerprint(w2)

            if not after.centers_solved:
                return fail(CENTER_NOT_RESTORED, "装配后中心未归面",
                            output_slot=out_slot, state_before=state_before,
                            state_after=after, goal=goal, setup_moves=setup_moves,
                            insert_moves=insert_moves, flip_moves=flip_moves,
                            replay_consistent=replay_ok,
                            centers_solved_after=after.centers_solved,
                            fixed_centers_preserved=after.fixed_centers_preserved)
            if not after.fixed_centers_preserved:
                return fail(FIXED_CENTER_MOVED, "固定面心被移动",
                            output_slot=out_slot, state_before=state_before,
                            state_after=after, goal=goal, setup_moves=setup_moves,
                            insert_moves=insert_moves, flip_moves=flip_moves,
                            replay_consistent=replay_ok,
                            centers_solved_after=after.centers_solved,
                            fixed_centers_preserved=after.fixed_centers_preserved)
            if not final_success:
                return fail(FLIP_FIX_FAILED, "flip-fix 后仍未配对或三块未同槽",
                            output_slot=out_slot, state_before=state_before,
                            state_after=after, goal=goal, setup_moves=setup_moves,
                            insert_moves=insert_moves, flip_moves=flip_moves,
                            replay_consistent=replay_ok,
                            centers_solved_after=after.centers_solved,
                            fixed_centers_preserved=after.fixed_centers_preserved)
            if not replay_ok:
                return fail(REPLAY_MISMATCH, "真实重放不一致",
                            output_slot=out_slot, state_before=state_before,
                            state_after=after, goal=goal, setup_moves=setup_moves,
                            insert_moves=insert_moves, flip_moves=flip_moves,
                            replay_consistent=False,
                            centers_solved_after=after.centers_solved,
                            fixed_centers_preserved=after.fixed_centers_preserved)

            side_effects = _protected_slots_affected(cube, w2)
            return CompleteTredgeResult(
                success=True, moves=all_moves, middle_piece_id=middle_piece_id,
                wing_a_piece_id=wing_a_piece_id, wing_b_piece_id=wing_b_piece_id,
                output_slot=out_slot, state_before=state_before, state_after=after,
                goal=goal, setup_moves=setup_moves, insert_moves=insert_moves,
                flip_moves=flip_moves, side_effects=side_effects,
                centers_solved_after=after.centers_solved,
                fixed_centers_preserved=after.fixed_centers_preserved,
                replay_consistent=True, error_code=None, message="ok",
            )

    # 尝试了全部目标仍未装配出三块同槽
    return fail(NO_GOAL_COMPLETED,
                "所有候选 (partial_slot, wing_entry) 均未能把三块装配到同一槽",
                state_before=state_before)
