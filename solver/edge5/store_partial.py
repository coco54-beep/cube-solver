"""确定性 free-slice 部分组合存储（Gate 4，range 判决：store + survival only）。

Gate 4 目标（用户裁定）：在固定工作布局（work=UF, open=2F, 入口=UR 右翼）下，给定一个
「中棱 + 翼-A」的 rel>=2 位置组合（通常由 `insert_wing_atomic` 产出于入口槽 UR），提供——
1. **store**：把该部分组合整体搬运到一个**安全且不被 2F 触碰**的存储槽（纯外层、与同槽
   翼一起带走、不复散）并恢复中心/固定面心；
2. **survival**：该存储组合在「对其它 piece 做一次 free-slice 开/关循环」后仍存活
   （不被拆散、关系不降）；
3. **recoverable**：该存储组合可被整体搬回工作带（用同样的纯外层 relocate），即第一关系
   在下一次 free-slice 后仍可恢复。

正确性约束（均须真实 Cube5 重放校验）：
- 只用物理合法动作（1X 外层 + 2X 宽层；绝不出现 3X/4X/5X）。
- 定位/存储 setup 只用纯外层 1X（天然保持中心归面与固定面心）。
- 本模块只读，不修改传入 cube。

存储目标槽 = `layout.storage_slots`（安全，`2F` 开/关都完整保留该槽组）中**不在**工作带
（staging_slots）的槽——即彻底不被 `2F` 触碰的槽（= safe-untouched）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .compact_state import state_of
from .freeslice_layout import (
    FreeSliceLayout, DEFAULT_LAYOUT, relocate_middle_to_pos,
    work_mid_pos,
)
from .positions import MIDDLE_ORDER, WING_ORDER, slot_of, slot, MIDDLE_INDEX
from .state import centers_are_color_solved
from .free_slice import _fixed_centers_preserved
from .atomic_insert import middle_wing_relation_real, REL_COMBO

# 错误码
PRECONDITION_FAILED = "PRECONDITION_FAILED"
RELATION_NOT_COMBO = "RELATION_NOT_COMBO"
STORE_TARGET_UNREACHABLE = "STORE_TARGET_UNREACHABLE"
COMBO_NOT_PRESERVED = "COMBO_NOT_PRESERVED"
CENTER_NOT_RESTORED = "CENTER_NOT_RESTORED"
FIXED_CENTER_MOVED = "FIXED_CENTER_MOVED"
REPLAY_MISMATCH = "REPLAY_MISMATCH"


def safe_untouched_slots(layout: Optional[FreeSliceLayout] = None) -> Tuple[str, ...]:
    """安全且不被 `2F` 触碰的存储槽 = storage_slots - staging_slots（排序）。"""
    layout = layout or DEFAULT_LAYOUT
    return tuple(sorted(set(layout.storage_slots) - set(layout.staging_slots)))


def _default_target_slot(middle_pos: int, layout: FreeSliceLayout) -> Optional[str]:
    """选出「从当前中棱位置可在 max_depth 内纯外层到达」的首个 safe-untouched 槽。"""
    for s in safe_untouched_slots(layout):
        tmid = MIDDLE_INDEX[slot(s).middle]
        if relocate_middle_to_pos(middle_pos, tmid) is not None:
            return s
    return None


def _cubie_by_home(cube, home_coord):
    for pos, cubie in cube.cubies.items():
        if cubie.home == home_coord:
            return cubie
    return None


def _full_state_fingerprint(cube) -> Tuple:
    return tuple(
        (p, cubie.home, tuple(sorted(cubie.stickers.items())))
        for p, cubie in sorted(cube.cubies.items())
    )


@dataclass
class StorePartialResult:
    success: bool
    moves: Tuple[str, ...]
    middle_piece_id: int
    wing_piece_id: int
    store_moves: Tuple[str, ...]
    combo_slot_before: Optional[str]
    combo_slot_after: Optional[str]
    relation_before: Optional[object]
    relation_after: Optional[object]
    centers_solved_after: bool
    fixed_centers_preserved: bool
    replay_consistent: bool
    error_code: Optional[str]
    message: str


def store_partial_combo(
    cube,
    *,
    middle_piece_id: int,
    wing_piece_id: int,
    layout: Optional[FreeSliceLayout] = None,
    target_slot: Optional[str] = None,
    max_depth: int = 8,
) -> StorePartialResult:
    """把「中棱 + 翼」的部分组合整体搬到安全存储槽（纯外层），保持组合与中心。

    不改写输入 cube。前置：中心归面 + 固定面心保持 + 中棱与翼已形成 rel>=2 组合。
    """
    layout = layout or DEFAULT_LAYOUT

    def fail(code, msg, **kw):
        return StorePartialResult(
            success=False, moves=(), middle_piece_id=middle_piece_id,
            wing_piece_id=wing_piece_id, store_moves=(),
            combo_slot_before=kw.get("combo_slot_before"),
            combo_slot_after=kw.get("combo_slot_after"),
            relation_before=kw.get("relation_before"),
            relation_after=kw.get("relation_after"),
            centers_solved_after=kw.get("centers_solved_after", False),
            fixed_centers_preserved=kw.get("fixed_centers_preserved", False),
            replay_consistent=kw.get("replay_consistent", False),
            error_code=code, message=msg,
        )

    if not centers_are_color_solved(cube):
        return fail(PRECONDITION_FAILED, "中心未归面")
    if not _fixed_centers_preserved(cube):
        return fail(PRECONDITION_FAILED, "固定面心已被移动")

    rel_before = middle_wing_relation_real(cube, middle_piece_id, wing_piece_id)
    if rel_before.relation_level < REL_COMBO or not rel_before.same_logical_slot:
        return fail(RELATION_NOT_COMBO, "中棱与翼尚未形成 rel>=2 同槽组合",
                    relation_before=rel_before)

    # 目标槽：默认一个 safe-untouched 且可达的槽
    if target_slot is None:
        mpos_now = _find_middle_pos(cube, middle_piece_id)
        target_slot = _default_target_slot(mpos_now, layout)
        if target_slot is None:
            return fail(STORE_TARGET_UNREACHABLE, "无可达的安全存储槽",
                        relation_before=rel_before)
    if target_slot not in safe_untouched_slots(layout):
        return fail(STORE_TARGET_UNREACHABLE,
                    f"目标槽 {target_slot} 不是 safe-untouched（会被 2F 触碰）",
                    relation_before=rel_before)

    st = state_of(cube)
    mpos = _find_middle_pos(cube, middle_piece_id)
    target_mid_pos = MIDDLE_INDEX[slot(target_slot).middle]
    store_moves = relocate_middle_to_pos(mpos, target_mid_pos, max_depth)
    if store_moves is None:
        return fail(STORE_TARGET_UNREACHABLE,
                    f"无法把中棱从位置 {mpos} 纯外层搬到 {target_slot}",
                    relation_before=rel_before)

    w = cube.clone()
    for mv in store_moves:
        w.apply_move(mv)

    rel_after = middle_wing_relation_real(w, middle_piece_id, wing_piece_id)
    centers_after = centers_are_color_solved(w)
    fixed_after = _fixed_centers_preserved(w)
    mid_cubie = _cubie_by_home(w, MIDDLE_ORDER[middle_piece_id])
    slot_after = slot_of(mid_cubie.pos) if mid_cubie else None

    replay = cube.clone()
    for mv in store_moves:
        replay.apply_move(mv)
    replay_ok = _full_state_fingerprint(replay) == _full_state_fingerprint(w)

    moves = tuple(store_moves)
    if slot_after != target_slot:
        return fail(COMBO_NOT_PRESERVED, f"存储后组合槽 {slot_after} != 目标 {target_slot}",
                    combo_slot_after=slot_after, relation_before=rel_before,
                    relation_after=rel_after, centers_solved_after=centers_after,
                    fixed_centers_preserved=fixed_after, replay_consistent=replay_ok)
    if not (rel_after.relation_level >= REL_COMBO):
        return fail(COMBO_NOT_PRESERVED, "存储后 rel<2：组合被拆散",
                    combo_slot_after=slot_after, relation_before=rel_before,
                    relation_after=rel_after, centers_solved_after=centers_after,
                    fixed_centers_preserved=fixed_after, replay_consistent=replay_ok)
    if not centers_after:
        return fail(CENTER_NOT_RESTORED, "存储后中心未归面",
                    combo_slot_after=slot_after, relation_before=rel_before,
                    relation_after=rel_after, centers_solved_after=centers_after,
                    fixed_centers_preserved=fixed_after, replay_consistent=replay_ok)
    if not fixed_after:
        return fail(FIXED_CENTER_MOVED, "固定面心被移动",
                    combo_slot_after=slot_after, relation_before=rel_before,
                    relation_after=rel_after, centers_solved_after=centers_after,
                    fixed_centers_preserved=fixed_after, replay_consistent=replay_ok)
    if not replay_ok:
        return fail(REPLAY_MISMATCH, "真实重放不一致",
                    combo_slot_after=slot_after, relation_before=rel_before,
                    relation_after=rel_after, centers_solved_after=centers_after,
                    fixed_centers_preserved=fixed_after, replay_consistent=replay_ok)

    return StorePartialResult(
        success=True, moves=moves, middle_piece_id=middle_piece_id,
        wing_piece_id=wing_piece_id, store_moves=tuple(store_moves),
        combo_slot_before=None, combo_slot_after=slot_after,
        relation_before=rel_before, relation_after=rel_after,
        centers_solved_after=centers_after, fixed_centers_preserved=fixed_after,
        replay_consistent=True, error_code=None, message="ok",
    )


def _find_middle_pos(cube, middle_piece_id: int) -> Optional[int]:
    st = state_of(cube)
    return next((j for j, v in enumerate(st.middle) if v == middle_piece_id), None)


def combo_survives_free_slice(
    cube,
    *,
    middle_piece_id: int,
    wing_piece_id: int,
    layout: Optional[FreeSliceLayout] = None,
    outer_body: Tuple[str, ...] = ("U", "F'", "U'"),
) -> bool:
    """对一个 free-slice 开/关循环（open + outer + close）后，存储组合是否仍存活。

    由于目标槽是 safe-untouched（`2F` 不动该槽），组合应保持 rel>=2 且同槽。
    只读，不改写 cube。
    """
    layout = layout or DEFAULT_LAYOUT
    w = cube.clone()
    w.apply_move(layout.open_move)
    for mv in outer_body:
        w.apply_move(mv)
    w.apply_move(layout.close_move)
    rel = middle_wing_relation_real(w, middle_piece_id, wing_piece_id)
    return rel.relation_level >= REL_COMBO and rel.same_logical_slot
