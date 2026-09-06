"""5x5 棱位置模型：36 个棱块，12 条逻辑棱（每条由 1 中棱 + 2 翼组成）。

坐标约定（5x5，maxc=6，坐标取值 {-6,-3,0,3,6}）：
- 中棱(middle)：恰好 2 个坐标绝对值==6，第三坐标 0（共 12 个）。
- 翼(wing)：恰好 2 个坐标绝对值==6，第三坐标 ±3（共 24 个）。
- 每条逻辑棱（两个面相交，如 UF）的坐标由该两个面的法线确定；
  中棱位于两法线层坐标 ±6、贯穿轴坐标 0 处；两翼位于贯穿轴 ±3 处。

槽名固定不变（依据坐标，与 cubie 当前颜色无关）：
    UF UR UB UL  DF DR DB DL  FR FL BR BL
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from cube.coordinates import FACE_AXIS_SIGN, coord_values, get_d_maxc

Coord = Tuple[int, int, int]

# 5x5 常数
_MAXC = 6
_WING_OFF = 3

# 12 条逻辑棱名（与 4x4/reduced 保持一致的前-后面顺序约定）。
SLOT_NAMES: Tuple[str, ...] = (
    "UF", "UR", "UB", "UL",
    "DF", "DR", "DB", "DL",
    "FR", "FL", "BR", "BL",
)


@dataclass(frozen=True)
class LogicalEdgeSlot:
    """一条逻辑棱槽：由固定坐标定义，不随颜色变化。"""

    name: str
    middle: Coord
    left_wing: Coord
    right_wing: Coord


def _slot_middle(name: str) -> Coord:
    """由槽名（两个面）给出中棱坐标。贯穿轴 = 未出现在两面的轴，坐标 0。"""
    axs = set()
    sgn = {}
    for f in name:
        ax, sg = FACE_AXIS_SIGN[f]
        axs.add(ax)
        sgn[ax] = sg
    through = ({0, 1, 2} - axs).pop()
    c = [0, 0, 0]
    for ax in axs:
        c[ax] = sgn[ax] * _MAXC
    return tuple(c)


def _slot_wings(name: str) -> Tuple[Coord, Coord]:
    """两个翼坐标：沿贯穿轴 ±_WING_OFF。"""
    m = _slot_middle(name)
    through = [i for i, v in enumerate(m) if v == 0][0]
    lw = list(m)
    lw[through] = -_WING_OFF
    rw = list(m)
    rw[through] = _WING_OFF
    return tuple(lw), tuple(rw)


def slot(name: str) -> LogicalEdgeSlot:
    """由槽名返回 LogicalEdgeSlot。"""
    m = _slot_middle(name)
    lw, rw = _slot_wings(name)
    return LogicalEdgeSlot(name, m, lw, rw)


# 槽名 -> LogicalEdgeSlot
SLOTS: Dict[str, LogicalEdgeSlot] = {name: slot(name) for name in SLOT_NAMES}

# 坐标 -> 槽名（36 个棱坐标，含中/左翼/右翼）
COORD_TO_SLOT: Dict[Coord, str] = {}
for name, s in SLOTS.items():
    COORD_TO_SLOT[s.middle] = name
    COORD_TO_SLOT[s.left_wing] = name
    COORD_TO_SLOT[s.right_wing] = name


def is_middle_pos(pos: Coord) -> bool:
    """是否为中棱位置（恰好 2 个坐标绝对值==6，第三坐标 0）。"""
    return sorted(abs(v) for v in pos) == [0, _MAXC, _MAXC]


def is_wing_pos(pos: Coord) -> bool:
    """是否为翼位置（恰好 2 个坐标绝对值==6，第三坐标 ±3）。"""
    return sorted(abs(v) for v in pos) == [_WING_OFF, _MAXC, _MAXC]


def slot_of(pos: Coord) -> str:
    """返回某个 36 棱坐标（中/翼）所属的逻辑棱名。"""
    try:
        return COORD_TO_SLOT[pos]
    except KeyError:
        raise ValueError("不是 5x5 棱位置: %s" % (pos,))


def edge_positions() -> List[Coord]:
    """返回全部 36 个棱位置（升序排序，确定性）。"""
    d, maxc = get_d_maxc(5)
    vals = coord_values(5)
    out = []
    for x in vals:
        for y in vals:
            for z in vals:
                pos = (x, y, z)
                if is_middle_pos(pos) or is_wing_pos(pos):
                    out.append(pos)
    return sorted(out)


# 稳定编号：中棱 12、翼 24（按排序坐标），供置换建模使用。
MIDDLE_ORDER: Tuple[Coord, ...] = tuple(sorted(p for p in edge_positions() if is_middle_pos(p)))
WING_ORDER: Tuple[Coord, ...] = tuple(sorted(p for p in edge_positions() if is_wing_pos(p)))

MIDDLE_INDEX: Dict[Coord, int] = {p: i for i, p in enumerate(MIDDLE_ORDER)}
WING_INDEX: Dict[Coord, int] = {p: i for i, p in enumerate(WING_ORDER)}


def edge_type_of_cubie(cubie) -> frozenset:
    """返回该棱块的色对（以 frozenset 表示，无色序）。仅适用于贴 2 面的棱块。"""
    return frozenset(cubie.stickers.values())


def color_pair_of_slot(name: str, face_colors: Dict[str, str]) -> frozenset:
    """返回某逻辑棱槽的 home 色对（该槽两面颜色构成的 frozenset）。"""
    return frozenset(face_colors[f] for f in name)
