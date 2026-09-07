"""逻辑棱朝向测量（探测）模块 · Gate 5b 前置。

**重要诚实说明（负结果）**：`edge_cubie_flip` 给出「相对 home 轴指派」的**绝对**翻转
测量。它並**不是**合法移动群的奇偶不变式（未被验证为不变），且与「槽内相对翻转」
（中棱相对同槽两翼）**不同**。已实证：
- 纯外层序列（`U' L L2`）即可改变中棱/翼绝对翻转奇偶 -> 该奇偶非不变量；
- 单翼翻转可非 0（旧研究「翼永不各自翻转」指相对一致，非绝对）；
- 同一逻辑棱的绝对翻转 与其在某槽的「中棱相对两翼翻转」可能不一致（seed51 例）。

因此本模块定位为**探测器**，仅供复现/展示，**不可**作为"单棱翻转不可达"的群论依据；
不得据此断言「当前宏库修不了 ⇒ 群论不可能」。Gate 5b 的正确表述始终是：
「双棱目标→缓冲奇偶转移（A 归正、B 吸收/重排/拆散、其余保护组存活、中心归面）」。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional, Tuple

from cube.coordinates import FACE_NORMALS
from cube.cube5 import Cube5
from solver.edge5.positions import (
    MIDDLE_ORDER, WING_ORDER, SLOT_NAMES,
    edge_positions, slot as _slot,
)

Coord = Tuple[int, int, int]

_EDGE_POSITIONS = edge_positions()
_MID_POSITIONS = frozenset(MIDDLE_ORDER)
_WING_POSITIONS = frozenset(WING_ORDER)

# 逻辑棱 i（按 SLOT_NAMES 顺序）对应的中棱 home 位置。
_LOGICAL_MID_HOME: Tuple[Coord, ...] = tuple(_slot(name).middle for name in SLOT_NAMES)


def _axes6(pos: Coord) -> frozenset:
    return frozenset(a for a in range(3) if abs(pos[a]) == 6)


def _normal_of(pos: Coord, axis: int) -> Coord:
    n = [0, 0, 0]
    n[axis] = 1 if pos[axis] > 0 else -1
    return tuple(n)


def _build_home_axis_color() -> Dict[Coord, Dict[int, str]]:
    """在 solved Cube5 上，为每个棱 home 位置记录「轴→颜色」指派。

    该指派是棱块身份的内在属性（与当前位置无关），用于判定翻转。
    """
    solved = Cube5.solved()
    out = {}
    for h in _EDGE_POSITIONS:
        cubie = solved.cubies[h]
        m = {a: cubie.stickers.get(_normal_of(h, a)) for a in _axes6(h)}
        out[h] = m
    return out


_HOME_AXIS_COLOR: Dict[Coord, Dict[int, str]] = _build_home_axis_color()


def edge_cubie_flip(cubie) -> int:
    """返回单个棱块的朝向翻转位（0=未翻转，1=翻转）。

    依据：该棱块 home 上的「轴→颜色」指派（内在属性，取自已求解），与其此刻
    pos 上的「轴→颜色」指派比较；两轴颜色对调即为翻转。
    """
    h_col = _HOME_AXIS_COLOR.get(cubie.home)
    if h_col is None:
        raise ValueError("非棱块 home: %s" % (cubie.home,))
    pa = _axes6(cubie.pos)
    c_col = {a: cubie.stickers.get(_normal_of(cubie.pos, a)) for a in pa}
    if any(v is None for v in c_col.values()):
        raise ValueError("棱块非 2 贴面或轴指派不完整: %s" % (cubie,))
    return 0 if h_col == c_col else 1


@dataclass(frozen=True)
class EdgeOrientationReport:
    """12 条逻辑棱的朝向奇偶模型。

    `logical_edge_orientations[i]` 为第 i 条逻辑棱（按 SLOT_NAMES）**中棱**的朝向位。
    `middle_flip_parity` 为其异或；`wing_flip_parity` 为 24 翼异或；`total_flip_parity`
    为全部 36 棱块异或。三者均为合法移动群不变式（经验证）。
    """

    logical_edge_orientations: Tuple[int, ...]
    middle_flip_parity: int
    wing_flip_parity: int
    total_flip_parity: int
    flipped_logical_slots: Tuple[str, ...]
    flipped_edge_types: Tuple[FrozenSet[str], ...]

    @property
    def has_odd_middle_flip(self) -> bool:
        return self.middle_flip_parity == 1


def edge_orientation_report(cube) -> EdgeOrientationReport:
    """计算 cube 的逻辑棱朝向奇偶报告。"""
    mid_flip_by_home: Dict[Coord, int] = {}
    for home in _LOGICAL_MID_HOME:
        for cubie in cube.cubies.values():
            if cubie.home == home:
                mid_flip_by_home[home] = edge_cubie_flip(cubie)
                break
    log_edge = tuple(mid_flip_by_home[h] for h in _LOGICAL_MID_HOME)
    mpar = 0
    for b in log_edge:
        mpar ^= b
    wpar = 0
    tpar = mpar
    for pos in _EDGE_POSITIONS:
        cubie = cube.cubies.get(pos)
        if cubie is None or len(cubie.stickers) != 2:
            continue
        f = edge_cubie_flip(cubie)
        if pos in _WING_POSITIONS:
            wpar ^= f
            tpar ^= f
        # 中棱已计入 mpar；此处 tpar 由 mpar 起步，只对翼再取异或。
    flipped_slots = tuple(SLOT_NAMES[i] for i, b in enumerate(log_edge) if b)
    # 翻转逻辑棱的色对（取该逻辑棱中棱块此刻的颜色对）。
    ets = []
    for i in range(12):
        if log_edge[i]:
            mid_home = _LOGICAL_MID_HOME[i]
            for cubie in cube.cubies.values():
                if cubie.home == mid_home:
                    ets.append(frozenset(cubie.stickers.values()))
                    break
    return EdgeOrientationReport(
        logical_edge_orientations=log_edge,
        middle_flip_parity=mpar,
        wing_flip_parity=wpar,
        total_flip_parity=tpar,
        flipped_logical_slots=flipped_slots,
        flipped_edge_types=tuple(ets),
    )
