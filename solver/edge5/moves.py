"""5x5 棱动作影响表：从真实 Cube5 引擎自动提取每个合法动作对棱/中心的影响。

EdgeMoveEffect 记录一个动作对棱子系统的置换与对已配棱/中心的扰动：
- middle_perm / wing_perm：稳定编号的置换（pos 下标 -> 当前位于该位置的块的编号）。
- touched_slots：该动作移动了哪些逻辑棱槽的任一位置。
- moves_middle / moves_wings：是否移动了中棱/翼。
- group_moved_whole / group_split：以「还原态」为参照，某槽的 3 个成员是否
  被整体搬运（仍同槽）或拆散。
- fixed_face_centers_preserved：六个绝对面心是否保持原位。
- center_corner_moved / center_edge_moved：是否扰动中心两个活动轨道。
- inverse_restores：该动作后紧接其逆，是否使棱回到恒等（对单动作恒真，用于校验）。

全部数据由实际应用动作到 Cube5 还原态得出，非手写置换。
"""

from typing import Dict, FrozenSet, Tuple

from dataclasses import dataclass

from cube.cube5 import Cube5

from .positions import (
    MIDDLE_INDEX,
    MIDDLE_ORDER,
    SLOT_NAMES,
    WING_INDEX,
    WING_ORDER,
    slot_of,
)

Coord = tuple


@dataclass(frozen=True)
class EdgeMoveEffect:
    move: str
    middle_perm: Tuple[int, ...]       # 12
    wing_perm: Tuple[int, ...]         # 24
    touched_slots: FrozenSet[str]
    moves_middle: bool
    moves_wings: bool
    group_moved_whole: FrozenSet[str]   # 被整体搬运的槽（还原态参照）
    group_split: FrozenSet[str]         # 被拆散的槽（还原态参照）
    fixed_face_centers_preserved: bool
    center_corner_moved: bool
    center_edge_moved: bool
    inverse_restores: bool


def build_edge_move_effect(move: str) -> EdgeMoveEffect:
    """对单个动作计算 EdgeMoveEffect（施加到还原态后的置换与扰动）。"""
    cube = Cube5.solved()
    cube.apply_move(move)

    # 中棱/翼置换
    middle_perm = tuple(MIDDLE_INDEX[cube.cubies[p].home] for p in MIDDLE_ORDER)
    wing_perm = tuple(WING_INDEX[cube.cubies[p].home] for p in WING_ORDER)

    # 被移动的位置
    moved_positions = set()
    for j, p in enumerate(MIDDLE_ORDER):
        if cube.cubies[p].home != p:
            moved_positions.add(p)
    for j, p in enumerate(WING_ORDER):
        if cube.cubies[p].home != p:
            moved_positions.add(p)
    touched_slots = frozenset(slot_of(p) for p in moved_positions)

    moves_middle = any(middle_perm[j] != j for j in range(len(MIDDLE_ORDER)))
    moves_wings = any(wing_perm[j] != j for j in range(len(WING_ORDER)))

    # 分组分析：以还原态为参照，某槽的 3 个成员是否仍聚于同一槽（整体搬运）或被拆散。
    groups_moved_whole = set()
    groups_split = set()
    for name in SLOT_NAMES:
        from .positions import slot
        s = slot(name)
        cur = set()
        for p in (s.middle, s.left_wing, s.right_wing):
            cur.add(slot_of(cube.cubies[p].home))
        if len(cur) == 1:
            groups_moved_whole.add(name)
        else:
            groups_split.add(name)

    # 固定面心是否保持
    fixed_centers_preserved = True
    for cubie in cube.cubies.values():
        if len(cubie.stickers) == 1 and sorted(abs(v) for v in cubie.home) == [0, 0, 6]:
            if cubie.pos != cubie.home:
                fixed_centers_preserved = False
                break

    # 中心活动轨道是否扰动：检查贴 1 面的 cubie 是否有 move 后不在 home 且
    # 其 home 属于中心角/边轨道。
    from solver.center5.orbits import kind_of_position, CenterOrbitKind
    center_corner_moved = False
    center_edge_moved = False
    for cubie in cube.cubies.values():
        if len(cubie.stickers) == 1:
            kind = kind_of_position(cubie.home)
            if cubie.pos != cubie.home:
                if kind == CenterOrbitKind.CORNER:
                    center_corner_moved = True
                elif kind == CenterOrbitKind.EDGE:
                    center_edge_moved = True

    # 单动作 + 逆应使棱回到恒等（校验用）
    inv = Cube5.solved()
    inv.apply_move(move)
    inv.apply_move(_inverse_of(move))
    back_to_identity = all(inv.cubies[p].home == p for p in MIDDLE_ORDER) and \
                       all(inv.cubies[p].home == p for p in WING_ORDER)
    return EdgeMoveEffect(
        move=move,
        middle_perm=middle_perm,
        wing_perm=wing_perm,
        touched_slots=touched_slots,
        moves_middle=moves_middle,
        moves_wings=moves_wings,
        group_moved_whole=frozenset(groups_moved_whole),
        group_split=frozenset(groups_split),
        fixed_face_centers_preserved=fixed_centers_preserved,
        center_corner_moved=center_corner_moved,
        center_edge_moved=center_edge_moved,
        inverse_restores=back_to_identity,
    )


def _inverse_of(move: str) -> str:
    from solver.center5.legal_moves import invert_move_string
    return invert_move_string(move)


def build_edge_move_effects(generators: Tuple[str, ...]) -> Dict[str, EdgeMoveEffect]:
    """对一组动作逐个构建影响表。"""
    return {m: build_edge_move_effect(m) for m in generators}


def apply_perm(state: Tuple[int, ...], perm: Tuple[int, ...]) -> Tuple[int, ...]:
    """把索引置换应用到状态：state[j] = state[perm[j]]。"""
    return tuple(state[perm[j]] for j in range(len(state)))


def apply_move_to_state(state: Tuple[int, ...], perm: Tuple[int, ...]) -> Tuple[int, ...]:
    """等价应用：返回新状态（先位置后块的约定）。"""
    return apply_perm(state, perm)
