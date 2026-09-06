"""5x5 棱配对状态判定。

两个语义（用户已确认须分离）：
- is_edge_paired(cube, slot)：槽内 3 个成员（1 中棱 + 2 翼）色对一致。
  不要求它们位于 home 槽。这就是降阶阶段的目标。
- is_edge_solved(cube, slot)：已经配对，且该色对正好属于这个逻辑槽。

依据前期研究：任一色对的 2 片翼永远彼此朝向一致，且整条棱装齐后朝向自动一致。
因此「配对」= 3 成员色对相同 + 朝向一致（把朝向一致性固化为校验，而非弃用）。
"""

from typing import Dict, FrozenSet, Optional

from cube.cube5 import Cube5
from cube.coordinates import FACE_AXIS_SIGN, FACE_NORMALS

from .positions import (
    SLOTS,
    LogicalEdgeSlot,
    edge_type_of_cubie,
    slot,
)

Coord = tuple

# 面轴对照用于取法线。
_FACES = ("U", "D", "F", "B", "R", "L")


def face_colors(cube: Cube5) -> Dict[str, str]:
    """从固定面心读取每个面的颜色（用于判定 home 槽色对）。

    固定面心 = 贴 1 面且 home 为绝对面心（坐标 `[0,0,6]` 类）。
    """
    colors: Dict[str, str] = {}
    for cubie in cube.cubies.values():
        if len(cubie.stickers) == 1 and sorted(abs(v) for v in cubie.home) == [0, 0, 6]:
            # 固定面心：恰有一个坐标绝对值 == 6。由 (轴, 符号) 反查面。
            for face, (axis, sign) in FACE_AXIS_SIGN.items():
                if cubie.home[axis] == sign * 6:
                    colors[face] = cubie.stickers.get(FACE_NORMALS[face])
                    break
    if len(colors) != 6:
        raise ValueError("未能从固定面心读取全部 6 面颜色: %s" % colors)
    return colors


def edge_type_at(cube: Cube5, pos: Coord) -> Optional[FrozenSet[str]]:
    """返回某位置的棱块色对；非棱块则返回 None。"""
    cubie = cube.cubies.get(pos)
    if cubie is None or len(cubie.stickers) != 2:
        return None
    return edge_type_of_cubie(cubie)


def face_of_position(pos: Coord) -> Optional[str]:
    """位置所在的「外露面」。一个位置若某坐标 |v|==6，属于该轴同侧的面。

    返回该面名（U/D/F/B/R/L），否则返回 None（不在某个主人的外层面上）。
    """
    for face, (axis, sign) in FACE_AXIS_SIGN.items():
        if pos[axis] == sign * 6:
            return face
    return None


def _piece_single_color(cubie) -> Optional[str]:
    """单贴面块的唯一颜色；非单贴面块返回 None。"""
    if len(cubie.stickers) != 1:
        return None
    return next(iter(cubie.stickers.values()))


def center_color_off(cube: Cube5) -> int:
    """中心「按颜色归面」的错位数。

    统计所有单贴面块（含 6 个固定面心），凡「所在面」的颜色 != 该块自身颜色
    记 1。外层动作只置换同面中心身份、不改变面色 -> 0；两层宽转会跨面色，>0。
    这是降阶求解真正的中心恢复目标（同色中心块无需回到唯一 home 槽）。
    """
    fc = face_colors(cube)
    off = 0
    for pos, cubie in cube.cubies.items():
        if len(cubie.stickers) != 1:
            continue
        col = _piece_single_color(cubie)
        face = face_of_position(pos)
        if face is None or face not in fc:
            # 位置不在任何一个外层面上（不可能，但防御），或颜色缺失：计错位。
            off += 1
            continue
        if col != fc[face]:
            off += 1
    return off


def center_identity_off(cube: Cube5) -> int:
    """中心「块身份是否回到唯一 home 槽」的错位数。

    只统计单贴面块且其 home 不是绝对面心（即活动中心），home【是】绝对面心者计 0。
    外层动作会旋转同面 8 个活动中心 -> 此值>0，但面色保持 -> center_color_off==0。
    """
    off = 0
    for cubie in cube.cubies.values():
        if len(cubie.stickers) != 1:
            continue
        if sorted(abs(v) for v in cubie.home) == [0, 0, 6]:
            continue  # 固定面心不参与
        if cubie.pos != cubie.home:
            off += 1
    return off


def centers_are_color_solved(cube: Cube5) -> bool:
    """中心是否已按颜色归面（降阶求解的目标）。"""
    return center_color_off(cube) == 0


def _have_all_three(cube: Cube5, s: LogicalEdgeSlot) -> bool:
    """槽内 3 个位置是否都被棱块占据。"""
    return all(cube.cubies.get(p) is not None and len(cube.cubies[p].stickers) == 2
               for p in (s.middle, s.left_wing, s.right_wing))


def _orientation_consistent(cube: Cube5, s: LogicalEdgeSlot) -> bool:
    """校验 3 成员对两个面的颜色指派一致（朝向一致）。"""
    for face in s.name:
        n = FACE_NORMALS[face]
        cols = set()
        for p in (s.middle, s.left_wing, s.right_wing):
            cubie = cube.cubies[p]
            col = cubie.stickers.get(n)
            if col is None:
                return False
            cols.add(col)
        if len(cols) != 1:
            return False
    return True


def is_edge_paired(cube: Cube5, slot_name: str) -> bool:
    """槽内 1 中 + 2 翼是否色对一致且朝向一致（不要求 home）。"""
    s = slot(slot_name)
    if not _have_all_three(cube, s):
        return False
    types = {edge_type_of_cubie(cube.cubies[p]) for p in (s.middle, s.left_wing, s.right_wing)}
    if len(types) != 1:
        return False
    return _orientation_consistent(cube, s)


def is_edge_solved(cube: Cube5, slot_name: str) -> bool:
    """已经配对，且色对属于该逻辑槽（即「配对且回 home」）。"""
    if not is_edge_paired(cube, slot_name):
        return False
    s = slot(slot_name)
    et = edge_type_of_cubie(cube.cubies[s.middle])
    home = frozenset(face_colors(cube)[f] for f in s.name)
    return et == home


def paired_count(cube: Cube5) -> int:
    """统计「已配对（不要求 home）」的逻辑棱数。"""
    from .positions import SLOT_NAMES
    return sum(1 for name in SLOT_NAMES if is_edge_paired(cube, name))


def solved_count(cube: Cube5) -> int:
    """统计「已配对且回 home」的逻辑棱数。"""
    from .positions import SLOT_NAMES
    return sum(1 for name in SLOT_NAMES if is_edge_solved(cube, name))


def all_edges_paired(cube: Cube5) -> bool:
    from .positions import SLOT_NAMES
    return all(is_edge_paired(cube, name) for name in SLOT_NAMES)


def all_edges_solved(cube: Cube5) -> bool:
    from .positions import SLOT_NAMES
    return all(is_edge_solved(cube, name) for name in SLOT_NAMES)
