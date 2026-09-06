"""联合搜索紧凑状态（Milestone 2.5）。

把 5x5 的「36 棱 + 54 中心单贴面块」系统压缩为三个并列的位置置换：
  - 中棱（12）：每位置上的块之 home 下标
  - 翼棱（24）：每位置上的块之 home 下标
  - 中心（54）：每位置上的块之 home 下标

三种子结构共用一套「动作 -> 置换表」，由 Cube5.solved() 上打一次动作推得，
从而在搜索中无需克隆整立方体即可前进。

本模块为「允许穿谷的分桶 beam」提供状态模型、评分与分桶键。
抽象状态只保留中/翼/中心的身份置换；每条候选路径最终仍须在完整 Cube5
上重放校验，以免抽象丢约束导致错误剪枝。
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
    slot,
)
from .state import face_colors, face_of_position

# ---------------------------------------------------------------------------
# 常量表
# ---------------------------------------------------------------------------

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
# 槽名 -> 其三个 home 成员对应的工作槽绝对坐标。
_SLOT_POS = {
    name: (slot(name).middle, slot(name).left_wing, slot(name).right_wing)
    for name in SLOT_NAMES
}
# 坐标 -> 所属「home 槽名」。
_POS_HOME_SLOT = {}
for name in SLOT_NAMES:
    for p in _SLOT_POS[name]:
        _POS_HOME_SLOT[p] = name
# 中/翼下标 -> 该下标当前 home 位置坐标。
_MID_HOME = {i: p for i, p in enumerate(MIDDLE_ORDER)}
_WING_HOME = {i: p for i, p in enumerate(WING_ORDER)}


def _make_move_tables() -> Dict[str, Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]]:
    """每个动作的中/翼/中心三种位置置换表。

    除既有的「1层外层 + 2层宽转」外，加入 3 层内层切片动作（`3U/3D/3L/3R/3F/3B`
    及其 `'`/`2`）。free-slice 边缘配对依赖这些纯内层切片来在带间搬运翼块；
    `cube` 模型原生支持它们。中心模块(冻结)不受影响。
    """
    tables = {}
    from solver.center5.legal_moves import LEGAL_5X5_CENTER_MOVES
    # 只用物理合法动作（外层 1X + 两层宽转 2X）。3X/4X/5X 会置换 6 个固定面心，
    # 属非物理状态，禁止进入紧凑搜索空间（见 tests/test_move_physical_semantics.py）。
    # 真正的 free-slice 原语是合法宽转 + 外层组合（2X / 2X X'），它们保持固定面心。
    for mv in list(LEGAL_5X5_CENTER_MOVES):
        c = Cube5.solved()
        c.apply_move(mv)
        mid = tuple(MIDDLE_INDEX[c.cubies[p].home] for p in MIDDLE_ORDER)
        wing = tuple(WING_INDEX[c.cubies[p].home] for p in WING_ORDER)
        cen = tuple(_CENTER_INDEX[c.cubies[p].home] for p in _CENTERS)
        tables[mv] = (mid, wing, cen)
    return tables


MOVE_TABLES = _make_move_tables()
MOVES = tuple(MOVE_TABLES.keys())

# 中心位置所属的面，以及该面的目标颜色（由固定面心读出，合法动作下恒定）。
_CENTER_FACE = tuple(face_of_position(p) for p in _CENTERS)
_solved_5x5 = Cube5.solved()
_face_to_color = face_colors(_solved_5x5)
CENTER_COLOR = tuple(_face_to_color[_CENTER_FACE[i]] for i in range(_N_CENTER))


@dataclass(frozen=True)
class CompactPairingState:
    """联合搜索的紧凑状态：中/翼/中心三个并列位置置换。"""

    middle: Tuple[int, ...]
    wing: Tuple[int, ...]
    center: Tuple[int, ...]

    @property
    def key(self) -> Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]:
        return (self.middle, self.wing, self.center)


def state_of(cube: Cube5) -> CompactPairingState:
    """读取当前立方体的中/翼/中心位置置换。"""
    mid = tuple(MIDDLE_INDEX[cube.cubies[p].home] for p in MIDDLE_ORDER)
    wing = tuple(WING_INDEX[cube.cubies[p].home] for p in WING_ORDER)
    cen = tuple(_CENTER_INDEX[cube.cubies[p].home] for p in _CENTERS)
    return CompactPairingState(mid, wing, cen)


def _apply_perm(state: tuple, perm: tuple) -> tuple:
    return tuple(state[perm[j]] for j in range(len(state)))


def step(state: CompactPairingState, mv: str) -> CompactPairingState:
    """返回执行动作 mv 后的新紧凑状态。"""
    pm, pw, pc = MOVE_TABLES[mv]
    return CompactPairingState(
        _apply_perm(state.middle, pm),
        _apply_perm(state.wing, pw),
        _apply_perm(state.center, pc),
    )


# ---------------------------------------------------------------------------
# 评价指标
# ---------------------------------------------------------------------------

def color_off(state: CompactPairingState) -> int:
    """中心「按颜色归面」的错位数（外层动作不影响，宽层跨面才计）。

    位置 j 上坐着「home 为 _CENTERS[v]」的块，其颜色为其 home 面的颜色；
    若该颜色 != 位置 j 所在面的颜色，计 1。
    """
    cen = state.center
    return sum(1 for j, v in enumerate(cen) if CENTER_COLOR[v] != CENTER_COLOR[j])


def center_off(state: CompactPairingState) -> int:
    """中心「按身份回 home 槽」的错位数。"""
    cen = state.center
    return sum(1 for j, v in enumerate(cen) if v != j)


def matched(state: CompactPairingState, target_home_slot: str, work_slot: str) -> int:
    """工作槽中属于目标色对的成员数。"""
    work_pos = set(_SLOT_POS[work_slot])
    tmid = _SLOT_MID[target_home_slot]
    tw1, tw2 = _SLOT_WINGS[target_home_slot]
    cnt = 0
    for j, v in enumerate(state.middle):
        if v == tmid and MIDDLE_ORDER[j] in work_pos:
            cnt += 1
    for j, v in enumerate(state.wing):
        if v in (tw1, tw2) and WING_ORDER[j] in work_pos:
            cnt += 1
    return cnt


def work_paired(state: CompactPairingState, work_slot: str) -> bool:
    """工作槽 3 个位置是否容纳了同一 home 槽（同一色对）的 3 个成员。"""
    mpos = slot(work_slot).middle
    lwpos = slot(work_slot).left_wing
    rwpos = slot(work_slot).right_wing
    hs = set()
    for pos in (mpos, lwpos, rwpos):
        if pos in MIDDLE_INDEX:
            j = MIDDLE_INDEX[pos]
            v = state.middle[j]
            hs.add(_POS_HOME_SLOT[MIDDLE_ORDER[v]])
        else:
            j = WING_INDEX[pos]
            v = state.wing[j]
            hs.add(_POS_HOME_SLOT[WING_ORDER[v]])
    return len(hs) == 1


def slot_of_piece(state: CompactPairingState, piece_kind: str, home_slot: str) -> Optional[str]:
    """返回某目标成员（中或翼，属 home_slot 槽）当前的逻辑槽名；找不到返回 None。"""
    if piece_kind == "middle":
        t = _SLOT_MID[home_slot]
        for j, v in enumerate(state.middle):
            if v == t:
                return _POS_HOME_SLOT[MIDDLE_ORDER[j]]
        return None
    tw1, tw2 = _SLOT_WINGS[home_slot]
    for j, v in enumerate(state.wing):
        if v in (tw1, tw2):
            return _POS_HOME_SLOT[WING_ORDER[j]]
    return None


# ---------------------------------------------------------------------------
# 评分与分桶
# ---------------------------------------------------------------------------

# 中心颜色错位的分档边界（按桶编号 0..4）。
_CENTER_BUCKET_EDGES = (1, 9, 17, 25)


def center_bucket(color_off_val: int) -> int:
    """把中心颜色错位数量映射到 0..4 档。"""
    for i, e in enumerate(_CENTER_BUCKET_EDGES):
        if color_off_val < e:
            return i
    return len(_CENTER_BUCKET_EDGES)


def valley_bucket(valley_depth: int) -> int:
    """把穿谷深度映射到 0..3 档（0 / 1-2 / 3-4 / 5+）。"""
    if valley_depth == 0:
        return 0
    if valley_depth <= 2:
        return 1
    if valley_depth <= 4:
        return 2
    return 3


def bucket_key(matched_val: int, color_off_val: int, valley_depth: int) -> Tuple[int, int, int]:
    """分桶键：(目标匹配成员数, 中心错位档, 穿谷深度档)。

    每个桶独立保留候选，防止「目标已聚集但中心无法恢复」的状态占满 beam。
    """
    return (matched_val, center_bucket(color_off_val), valley_bucket(valley_depth))


def score_state(
    matched_val: int,
    color_off_val: int,
    valley_depth: int,
    path_length: int,
    piece_slot_distance: int = 0,
) -> Tuple[object, ...]:
    """非单调评分：优先接近目标，但不构成硬约束，允许穿越山谷。

    元组按字典序比较，故第一个维度优先级最高。
    """
    goal_reached = 1 if (matched_val == 3 and color_off_val == 0) else 0
    return (
        goal_reached,
        matched_val,
        -color_off_val,
        -valley_depth,
        -path_length,
        -piece_slot_distance,
    )


# 目标色对 -> home 槽
def target_home_slot(cube: Cube5, target: FrozenSet[str]) -> Optional[str]:
    """返回色对 == target 所对应的 home 逻辑槽名。"""
    fc = face_colors(cube)
    for name in SLOT_NAMES:
        if color_pair_of_slot(name, fc) == target:
            return name
    return None
