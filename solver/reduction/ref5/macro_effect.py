"""MacroEffect：宏在复原态上的完整置换效果（Plan 4）。

对一条由可执行动作组成的宏，在复原 5x5 上重放后计算：
- middle_permutation：中棱位置 -> 占据该位置的 cubie.home（身份）
- left_wing_permutation / right_wing_permutation：左/右翼轨道各自置换
- middle_orientation_delta / 两侧翼：相对槽原生朝向的翻转
- center_permutation：六固定面心是否被搬动
- affected_slots / move_count

关键判定 `moves_whole_slots`：若 M / LW / RW 三者执行完全相同置换，则宏只是
整体搬运完整槽单元，对「中棱↔翼相对归属」无修复价值（Plan 4 直接淘汰）。

宏动作以可执行 token 列表表示，支持：
- 面/宽转记号（`R`/`2R`/`u`…）经 `cube.apply_move`
- 物理内层切片（`M`/`E`/`S` 及带后缀）经 `cube.apply_inner_slice`
- 其余无法解析的 token 抛错

仅供研究 oracle。与生产 `solver/edge5` 搜索类无关。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from cube.cube5 import Cube5
from cube.middle_slice import SLICE_TOKENS, slice_turns
from solver.edge5.positions import (
    MIDDLE_ORDER,
    WING_ORDER,
    slot,
    slot_of,
    edge_type_of_cubie,
)

Coord = Tuple[int, int, int]

# 每个槽的左/右翼坐标（按 positions.slot 的定义）。
SLOT_NAMES: Tuple[str, ...] = tuple(slot(n).name for n in (
    "UF", "UR", "UB", "UL", "DF", "DR", "DB", "DL", "FR", "FL", "BR", "BL",
))
MID_POS: Dict[str, Coord] = {n: slot(n).middle for n in SLOT_NAMES}
LWING_POS: Dict[str, Coord] = {n: slot(n).left_wing for n in SLOT_NAMES}
RWING_POS: Dict[str, Coord] = {n: slot(n).right_wing for n in SLOT_NAMES}


@dataclass
class MacroEffect:
    middle_perm: Dict[str, str]          # 槽名 -> 占位中棱的 home 槽名
    left_wing_perm: Dict[str, str]       # 槽名 -> 占位左翼的 home 槽名
    right_wing_perm: Dict[str, str]
    middle_flip: Dict[str, bool]         # 槽名 -> 中棱是否相对 home 翻转
    left_flip: Dict[str, bool]
    right_flip: Dict[str, bool]
    centers_ok: bool                     # 中心归面
    fixed_centers_ok: bool               # 六固定面心不动
    moved_centers: bool                  # 中心是否被置换（非 identity）
    move_count: int
    raw_moves: List[str] = field(default_factory=list)

    @property
    def affected_slots(self) -> Tuple[str, ...]:
        """中棱/翼被搬动的槽集合。"""
        out = sorted({
            s for s in SLOT_NAMES
            if (self.middle_perm.get(s) != s
                or self.left_wing_perm.get(s) != s
                or self.right_wing_perm.get(s) != s)
        })
        return tuple(out)

    def moves_whole_slots(self) -> bool:
        """中棱、左翼、右翼三者执行完全相同置换（整体搬槽，无修复价值）。"""
        return all(
            self.middle_perm[s] == self.left_wing_perm[s] == self.right_wing_perm[s]
            for s in SLOT_NAMES
        )

    def middle_cycles(self) -> List[List[str]]:
        """中棱置换的循环分解（长度>=2 的循环，槽名表示）。"""
        return _cycles(self.middle_perm)

    def left_wing_cycles(self) -> List[List[str]]:
        return _cycles(self.left_wing_perm)

    def right_wing_cycles(self) -> List[List[str]]:
        return _cycles(self.right_wing_perm)

    def center_cycles(self) -> List[List[str]]:
        return []


def _cycles(perm: Dict[str, str]) -> List[List[str]]:
    seen = set()
    out = []
    for s in SLOT_NAMES:
        if s in seen:
            continue
        cur = s
        cy = []
        while cur not in seen:
            seen.add(cur)
            cy.append(cur)
            cur = perm[cur]
        if len(cy) > 1:
            out.append(cy)
    return out


def _home_slot_of_cubie(cubie) -> str:
    """给定 cubie，返回其 home 位置所属槽名。"""
    try:
        return slot_of(cubie.home)
    except ValueError:
        return None


def apply_token(cube, token: str) -> None:
    if token and token[0] in SLICE_TOKENS:
        axis, turns = slice_turns(token)
        if turns == 0:
            raise ValueError(f"非法切片后缀: {token!r}")
        cube.apply_inner_slice(axis, turns)
    else:
        cube.apply_move(token)


def apply_macro(cube, moves: List[str]) -> None:
    for tk in moves:
        apply_token(cube, tk)


def compute_effect(moves: List[str]) -> MacroEffect:
    """在复原 5x5 上重放宏，返回完整效果。"""
    from solver.edge5.state import centers_are_color_solved
    from solver.edge5.free_slice import _fixed_centers_preserved

    c = Cube5.solved()
    centers_before = centers_are_color_solved(c)

    # 记录初始各位置占位 cubie 的 home 槽（复原态 = 自身）
    # 复原态下 home slot 即位置槽名。

    apply_macro(c, moves)

    mid_perm = {}
    for s in SLOT_NAMES:
        cub = c.cubie_at(MID_POS[s])
        mid_perm[s] = _home_slot_of_cubie(cub) or s
    lw_perm = {}
    for s in SLOT_NAMES:
        cub = c.cubie_at(LWING_POS[s])
        lw_perm[s] = _home_slot_of_cubie(cub) or s
    rw_perm = {}
    for s in SLOT_NAMES:
        cub = c.cubie_at(RWING_POS[s])
        rw_perm[s] = _home_slot_of_cubie(cub) or s

    # 朝向 delta：不与 home 槽原生色方向一致即为翻转。
    from cube.cubie_model import is_fixed_face_center
    # 面原生色
    from cube.coordinates import FACE_AXIS_SIGN, FACE_NORMALS
    inv_axis = {v: k for k, v in FACE_AXIS_SIGN.items()}
    face_color = {}
    for cub in c.cubies.values():
        if is_fixed_face_center(cub):
            axis = [i for i, v in enumerate(cub.pos) if v != 0][0]
            sg = 1 if cub.pos[axis] > 0 else -1
            fc = inv_axis.get((axis, sg))
            if fc is not None:
                face_color[fc] = list(cub.stickers.values())[0]

    def flip_map(pos_by_slot, slot_of_face):
        out = {}
        for s in SLOT_NAMES:
            pos = pos_by_slot[s]
            cub = c.cubie_at(pos)
            if cub is None:
                out[s] = False
                continue
            # 该位置上 cubie 的 home 槽两面的原生色方向
            home_name = _home_slot_of_cubie(cub) or s
            native = [face_color.get(home_name[0]), face_color.get(home_name[1])]
            # 该 cubie 朝 home 两面的 sticker
            cols = set()
            for fch in set(home_name):
                normal = FACE_NORMALS[fch]
                if normal in cub.stickers:
                    cols.add(cub.stickers[normal])
            # 翻转判据：cubie 在 pos 上朝 home 两面法线的颜色是否覆盖 home 两面原生色
            out[s] = not (set(native) <= cols)
        return out

    mid_flip = flip_map(MID_POS, None)
    lw_flip = flip_map(LWING_POS, None)
    rw_flip = flip_map(RWING_POS, None)

    # 中心是否被置换：固定面心颜色是否仍一一对应
    centers_ok = centers_are_color_solved(c)
    fixed_ok = _fixed_centers_preserved(c)
    moved_centers = fixed_ok and False  # 这里用 centers_ok 判定是否归面

    return MacroEffect(
        middle_perm=mid_perm,
        left_wing_perm=lw_perm,
        right_wing_perm=rw_perm,
        middle_flip=mid_flip,
        left_flip=lw_flip,
        right_flip=rw_flip,
        centers_ok=centers_ok,
        fixed_centers_ok=fixed_ok,
        moved_centers=not centers_ok,
        move_count=len(moves),
        raw_moves=list(moves),
    )
