"""5x5 完整逻辑棱（tredge）分类工具（reference oracle 用）。

一条逻辑棱 = 1 中棱 + 2 翼，共 3 块同色对的棱块。本模块提供：

- `middle_edge_key` / `wing_edge_key`：取该槽中棱 / 某侧翼的"颜色对"（无序，仅识别身份）。
- `is_complete_tredge`：中棱与两翼属于同一条逻辑棱（颜色对一致）。
- `count_complete_tredges`：全 12 槽中完整 tredge 的数量。
- `tredge_oriented`：完整 tredge 三块在槽上的朝向是否与 home 朝向一致。

颜色对识别（身份）与方向判断是两回事：颜色对用无序色对判断"这是哪条逻辑棱的块"；
方向判断则要求三块朝各个面的 sticker 颜色与槽的原生色方向一致。二者不混用。

与 `solver/edge5` 的**搜索类**无关，只复用 `solver.edge5.positions` 的纯数据定义
（槽坐标 / 逻辑棱槽）。供研究 oracle 与测试引用。
"""
from __future__ import annotations

from typing import Optional, Tuple

from cube.cube5 import Cube5
from solver.edge5.positions import slot, slot_of

SLOT_NAMES: Tuple[str, ...] = tuple(slot(n).name for n in (
    "UF", "UR", "UB", "UL", "DF", "DR", "DB", "DL", "FR", "FL", "BR", "BL",
))


def _slot_info(name: str):
    return slot(name)


def middle_pos(state: Cube5, name: str):
    return _slot_info(name).middle


def _cubie(state: Cube5, pos):
    return state.cubies.get(pos)


def middle_edge_key(state: Cube5, name: str) -> Optional[frozenset]:
    """目标槽中棱的无序颜色对；无中棱块返回 None。"""
    c = _cubie(state, middle_pos(state, name))
    if c is None or len(c.stickers) != 2:
        return None
    return frozenset(c.stickers.values())


def wing_edge_key(state: Cube5, name: str, side: str) -> Optional[frozenset]:
    """目标槽某侧翼（side in {"left","right"}）的无序颜色对；无块返回 None。"""
    info = _slot_info(name)
    pos = info.left_wing if side == "left" else info.right_wing
    c = _cubie(state, pos)
    if c is None or len(c.stickers) != 2:
        return None
    return frozenset(c.stickers.values())


def wing_keys_of_slot(state: Cube5, name: str) -> Tuple[Optional[frozenset], Optional[frozenset]]:
    return (wing_edge_key(state, name, "left"), wing_edge_key(state, name, "right"))


def is_complete_tredge(state: Cube5, name: str) -> bool:
    """中棱与两翼是否属于同一条逻辑棱（颜色对一致），缺任何一块则为 False。"""
    mk = middle_edge_key(state, name)
    lw, rw = wing_keys_of_slot(state, name)
    if mk is None or lw is None or rw is None:
        return False
    return mk == lw == rw


def count_complete_tredges(state: Cube5) -> int:
    return sum(1 for n in SLOT_NAMES if is_complete_tredge(state, n))


def complete_tredge_slots(state: Cube5) -> set:
    return {n for n in SLOT_NAMES if is_complete_tredge(state, n)}


def tredge_oriented(state: Cube5, name: str) -> bool:
    """完整 tredge 三块是否朝向与槽原生色一致。

    仅当 `is_complete_tredge` 为真时有意义：判断中棱与两翼朝槽两面（如 UF 的 U、F）
    的 sticker 颜色是否等于这两个面的原生颜色，从而可被降阶为一整条同向 tredge。
    """
    if not is_complete_tredge(state, name):
        return False
    info = _slot_info(name)
    faces = (name[0], name[1])
    from cube.coordinates import FACE_NORMALS
    normals = [FACE_NORMALS[f] for f in faces]
    fixed = face_colors(state)
    for normal, f in zip(normals, faces):
        want = fixed.get(f)
        if want is None:
            return False
        for pos in (info.middle, info.left_wing, info.right_wing):
            c = _cubie(state, pos)
            if c is None or c.stickers.get(normal) != want:
                return False
    return True


def face_colors(state: Cube5) -> dict:
    """由六个固定面心颜色得出 face -> color。"""
    from cube.coordinates import FACE_AXIS_SIGN
    from cube.cubie_model import is_fixed_face_center
    inv = {v: k for k, v in FACE_AXIS_SIGN.items()}
    out = {}
    for c in state.cubies.values():
        if is_fixed_face_center(c):
            axis = [i for i, v in enumerate(c.pos) if v != 0][0]
            sys = 1 if c.pos[axis] > 0 else -1
            face = inv.get((axis, sys))
            if face is not None:
                out[face] = list(c.stickers.values())[0]
    return out

