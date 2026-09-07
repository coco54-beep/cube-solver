"""确定性 free-slice 原子插翼（Gate 3）。

IEEE Gate 3 目标：在固定工作布局（work_slot=UF, open=2F, 入口=UR 右翼位）下，把
**一条**目标翼以「原子」方式与目标中棱组合为 rel>=2（位置组合）。由用户裁定：
- rel=2（中棱+单翼同槽且色对一致）作为原子插翼成功标准；
- **朝向一致性推迟到 rel=3**（完整 tredge，即第二条翼到位时才强制），
  故 rel=2 阶段 `orientation_consistent` 允许为 False（由 `relation_level` 记录）。

正确性约束（贯穿本模块，均须在真实 Cube5 上重放校验）：
- 只用物理合法动作（1X 外层 + 2X 宽层；绝不出现 3X/4X/5X，它们会移动固定面心）。
- 定位 setup 只用纯外层 1X（天然保持中心归面与固定面心）。
- free-slice 本体 = `2F + outer + 2F'`（开/关切片），关切片后中心恢复归面。
- 8 项后置：relation_after>=2 且 > relation_before、中棱与翼保持同槽（组合不散）、
  中心归面、固定面心保持、动作合法、真实重放一致、不改写输入。

错误码见 `AtomicWingInsertResult.error_code`（见各常量）。本模块只读，不修改传入 cube。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .compact_state import state_of
from .freeslice_layout import FreeSliceLayout, DEFAULT_LAYOUT
from .positions import (
    MIDDLE_ORDER, WING_ORDER, slot_of, edge_type_of_cubie,
)
from .state import centers_are_color_solved
from .free_slice import _fixed_centers_preserved
from cube.coordinates import FACE_NORMALS

# 关系等级常量（GATE3 语义，与 free_slice 的抽象 rel 分级一致但不相同）
REL_SCATTERED = 0   # 三块不同槽（目标中棱与目标翼不同槽）
REL_SAME_SLOT = 1   # 同槽但色对不符（装错位置）
REL_COMBO = 2       # 同槽 + 色对一致（位置组合，rel=2；朝向可能翻转）
REL_ORIENTED = 3    # 同槽 + 色对一致 + 朝向一致（完整正确，rel=3 才强制）

# 错误码
JOINT_SETUP_UNREACHABLE = "JOINT_SETUP_UNREACHABLE"
PRECONDITION_FAILED = "PRECONDITION_FAILED"
INSERT_RELATION_NOT_IMPROVED = "INSERT_RELATION_NOT_IMPROVED"
MIDDLE_NOT_PRESERVED = "MIDDLE_NOT_PRESERVED"
CENTER_NOT_RESTORED = "CENTER_NOT_RESTORED"
FIXED_CENTER_MOVED = "FIXED_CENTER_MOVED"
REPLAY_MISMATCH = "REPLAY_MISMATCH"

# Gate 1 实证的 free-slice 本体（open + outer + close）
# outer = ("U", "F'", "U'")，经实证对 UF 工作槽稳定产出 rel>=2 位置组合于 UR。
_INSERT_OUTER = ("U", "F'", "U'")


@dataclass(frozen=True)
class WingRelation:
    """目标中棱与目标翼之间的真实装配关系（含位置 + 色对 + 朝向）。

    朝向一致仅在 rel=3 才强制；rel=2 时 `orientation_consistent` 允许为 False。
    """

    same_logical_slot: bool
    color_pair_matches: bool
    orientation_consistent: bool
    relation_level: int

    @property
    def is_combo(self) -> bool:
        """是否达到 rel>=2（位置组合：同槽且色对一致）。"""
        return self.relation_level >= REL_COMBO


def _cubie_by_home(cube, home_coord) -> Optional[object]:
    for pos, cubie in cube.cubies.items():
        if cubie.home == home_coord:
            return cubie
    return None


def _level_of(same: bool, pair: bool, orient: bool) -> int:
    if same and pair and orient:
        return REL_ORIENTED
    if same and pair:
        return REL_COMBO
    if same:
        return REL_SAME_SLOT
    return REL_SCATTERED


def middle_wing_relation_real(cube, middle_piece_id: int, wing_piece_id: int) -> WingRelation:
    """在真实 Cube5 上计算指定中棱 piece 与指定翼 piece 的装配关系。

    middle_piece_id / wing_piece_id 为 home 下标（见 compact_state._SLOT_MID / _SLOT_WINGS）。
    若目标 piece 找不到，返回 SCATTERED（视为不同槽）。只读，不改写 cube。
    """
    mid_cubie = _cubie_by_home(cube, MIDDLE_ORDER[middle_piece_id])
    wing_cubie = _cubie_by_home(cube, WING_ORDER[wing_piece_id])
    if mid_cubie is None or wing_cubie is None:
        return WingRelation(False, False, False, REL_SCATTERED)
    try:
        ms = slot_of(mid_cubie.pos)
        ws = slot_of(wing_cubie.pos)
    except ValueError:
        return WingRelation(False, False, False, REL_SCATTERED)
    same = ms == ws
    pair = edge_type_of_cubie(mid_cubie) == edge_type_of_cubie(wing_cubie)
    orient = False
    if same and pair:
        orient = True
        for face in ms:
            n = FACE_NORMALS[face]
            mcol = mid_cubie.stickers.get(n)
            wcol = wing_cubie.stickers.get(n)
            if mcol is None or wcol is None or mcol != wcol:
                orient = False
                break
    return WingRelation(same, pair, orient, _level_of(same, pair, orient))


def _insert_moves(layout: FreeSliceLayout) -> Tuple[str, ...]:
    return (layout.open_move,) + _INSERT_OUTER + (layout.close_move,)


@dataclass
class AtomicWingInsertResult:
    success: bool
    moves: Tuple[str, ...]
    middle_piece_id: int
    wing_piece_id: int
    setup_moves: Tuple[str, ...]
    insert_moves: Tuple[str, ...]
    relation_before: Optional[WingRelation]
    relation_after: Optional[WingRelation]
    middle_preserved: bool
    centers_solved_after: bool
    fixed_centers_preserved: bool
    replay_consistent: bool
    error_code: Optional[str]
    message: str


def _full_state_fingerprint(cube) -> Tuple:
    return tuple(
        (p, cubie.home, tuple(sorted(cubie.stickers.items())))
        for p, cubie in sorted(cube.cubies.items())
    )


def insert_wing_atomic(
    cube,
    *,
    middle_piece_id: int,
    wing_piece_id: int,
    layout: Optional[FreeSliceLayout] = None,
) -> AtomicWingInsertResult:
    """把目标中棱与目标翼做一次确定性原子插翼（rel>=2 位置组合）。

    流程：纯外层「定位 setup」把中棱送入工作槽（UF）、翼送入入口（UR 右翼位）；
    随后 `2F + outer + 2F'` 关切片开/关，把翼组合到中棱（同槽 + 色对一致）。

    不改写输入 cube（全程 clone）。失败时返回指定 error_code，
    `success=False`（详见各 # 后置）。成功时 `success=True`。
    """
    layout = layout or DEFAULT_LAYOUT

    def fail(code, msg, **kw):
        return AtomicWingInsertResult(
            success=False,
            moves=(),
            middle_piece_id=middle_piece_id,
            wing_piece_id=wing_piece_id,
            setup_moves=(),
            insert_moves=(),
            relation_before=kw.get("relation_before"),
            relation_after=kw.get("relation_after"),
            middle_preserved=False,
            centers_solved_after=kw.get("centers_solved_after", False),
            fixed_centers_preserved=kw.get("fixed_centers_preserved", False),
            replay_consistent=kw.get("replay_consistent", False),
            error_code=code,
            message=msg,
        )

    # 前置：中心归面 + 固定面心保持
    if not centers_are_color_solved(cube):
        return fail(PRECONDITION_FAILED, "中心未归面")
    if not _fixed_centers_preserved(cube):
        return fail(PRECONDITION_FAILED, "固定面心已被移动")

    relation_before = middle_wing_relation_real(cube, middle_piece_id, wing_piece_id)

    # 联合定位 setup（纯外层 BFS 表，键为位置下标）
    st = state_of(cube)
    mpos = next((j for j, v in enumerate(st.middle) if v == middle_piece_id), None)
    wpos = next((j for j, v in enumerate(st.wing) if v == wing_piece_id), None)
    if mpos is None or wpos is None:
        return fail(JOINT_SETUP_UNREACHABLE, "找不到目标中棱/翼 piece", relation_before=relation_before)
    setup = layout.joint_setup.get((mpos, wpos))
    if setup is None:
        message = "联合 setup 不可达（结构不变量），需先重定位"
        return fail(JOINT_SETUP_UNREACHABLE, message, relation_before=relation_before)

    # 应用 setup + free-slice 本体
    insert_moves = _insert_moves(layout)
    w = cube.clone()
    for mv in setup:
        w.apply_move(mv)
    for mv in insert_moves:
        w.apply_move(mv)

    relation_after = middle_wing_relation_real(w, middle_piece_id, wing_piece_id)
    centers_after = centers_are_color_solved(w)
    fixed_after = _fixed_centers_preserved(w)
    middle_preserved = relation_after.same_logical_slot

    moves = tuple(setup) + tuple(insert_moves)

    # 真实重放一致：在原始 cube 的独立 clone 上重放 moves，比较完整物理态
    replay = cube.clone()
    for mv in moves:
        replay.apply_move(mv)
    replay_consistent = _full_state_fingerprint(replay) == _full_state_fingerprint(w)

    # 后置验收（按错误码优先级）
    if not relation_after.is_combo:
        return fail(INSERT_RELATION_NOT_IMPROVED, "rel<2：中棱与翼未形成位置组合",
                    relation_before=relation_before, relation_after=relation_after,
                    centers_solved_after=centers_after, fixed_centers_preserved=fixed_after,
                    replay_consistent=replay_consistent)
    if not (relation_after.relation_level > relation_before.relation_level):
        return fail(INSERT_RELATION_NOT_IMPROVED, "rel 未严格提升",
                    relation_before=relation_before, relation_after=relation_after,
                    centers_solved_after=centers_after, fixed_centers_preserved=fixed_after,
                    replay_consistent=replay_consistent)
    if not middle_preserved:
        return fail(MIDDLE_NOT_PRESERVED, "中棱未与翼保持同槽",
                    relation_before=relation_before, relation_after=relation_after,
                    centers_solved_after=centers_after, fixed_centers_preserved=fixed_after,
                    replay_consistent=replay_consistent)
    if not centers_after:
        return fail(CENTER_NOT_RESTORED, "关切片后中心未归面",
                    relation_before=relation_before, relation_after=relation_after,
                    centers_solved_after=centers_after, fixed_centers_preserved=fixed_after,
                    replay_consistent=replay_consistent)
    if not fixed_after:
        return fail(FIXED_CENTER_MOVED, "固定面心被移动",
                    relation_before=relation_before, relation_after=relation_after,
                    centers_solved_after=centers_after, fixed_centers_preserved=fixed_after,
                    replay_consistent=replay_consistent)
    if not replay_consistent:
        return fail(REPLAY_MISMATCH, "真实重放不一致",
                    relation_before=relation_before, relation_after=relation_after,
                    centers_solved_after=centers_after, fixed_centers_preserved=fixed_after,
                    replay_consistent=replay_consistent)

    return AtomicWingInsertResult(
        success=True,
        moves=moves,
        middle_piece_id=middle_piece_id,
        wing_piece_id=wing_piece_id,
        setup_moves=tuple(setup),
        insert_moves=tuple(insert_moves),
        relation_before=relation_before,
        relation_after=relation_after,
        middle_preserved=middle_preserved,
        centers_solved_after=centers_after,
        fixed_centers_preserved=fixed_after,
        replay_consistent=True,
        error_code=None,
        message="ok",
    )
