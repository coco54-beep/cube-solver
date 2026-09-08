"""Gate 5c：允许过程破中心、终态恢复中心且改变「中棱↔翼归属」的切片宏搜索。

按用户指定顺序：
1. 基础短 commutator `[A, B] = A B A' B'`，A 为单内层切片，B 为外层短序列；
2. 再枚举共轭 `X [A, B] X'`（X 为外层 setup）。

内部统一用物理层编号 `LayerTurn(axis, layer, turns)`（axis=x/y/z，layer 从最外层
向内 0..2，turns=1/2/3），末尾再映射为可执行动作串。

终态过滤条件：
- centers_solved(final)
- fixed_centers_unchanged(final)
- relative_middle_wing_assignment_changed(initial, final)
- （可选）影响的槽数少

本文件为研究脚本，不进入生产求解器。以 `python <file>` 直接运行。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from cube.cube5 import Cube5
from cube.middle_slice import apply_physical_sequence
from solver.edge5.state import centers_are_color_solved
from solver.edge5.free_slice import _fixed_centers_preserved

# 单内层切片动作（贯穿轴 0 的切片）：axis, turns。
SLICE_ACTIONS: List[Tuple[str, int]] = [
    ("x", 1), ("x", 2), ("x", 3),
    ("y", 1), ("y", 2), ("y", 3),
    ("z", 1), ("z", 2), ("z", 3),
]
# 外层单层动作（最外层，turns 1/2/3），以记号 + 逆记号为基底。
OUTER_BASIS: List[str] = ["R", "U", "F", "L", "D", "B", "R'", "U'", "F'", "L'", "D'", "B'"]

# LayerTurn -> 执行
def layer_turn_moves(axis: str, layer: int, turns: int) -> List[str]:
    """物理层编号 -> 可执行动作串。

    layer==0（贯穿轴中央切片）用 apply_inner_slice；layer==最外层用面记号。
    """
    if layer == 0:
        # 由 middle_slice 直接以物理轴+圈数应用
        return [("SLICE", axis, turns)]
    # 外层：axis x/y/z -> 面 R/U/F（layer==2 为最外层）
    # 这里只处理最外层；layer 1（宽二）暂不在此扫描用（后续扩展）。
    face = {"x": "R", "y": "U", "z": "F"}[axis]
    suffix = "" if turns == 1 else ("2" if turns == 2 else "'")
    return [face + suffix]


def apply_moveset(cube, moves: List) -> None:
    for mv in moves:
        if mv[0] == "SLICE":
            cube.apply_inner_slice(mv[1], mv[2])
        else:
            cube.apply_move(mv)


def mismatch_count(cube) -> int:
    """中棱颜色对 ≠ 该槽两翼颜色对的槽数（归属改变量）。"""
    from collections import defaultdict
    from solver.edge5.positions import slot_of, edge_type_of_cubie
    from solver.edge5.positions import MIDDLE_ORDER
    by = defaultdict(list)
    # 每个槽的 中棱 + 两翼 颜色对
    # 用 pos 映射到槽
    t = None
    import importlib.util, os
    spec = importlib.util.spec_from_file_location(
        "tredge", os.path.join(os.path.dirname(__file__), "tredge.py"))
    tr = importlib.util.module_from_spec(spec); spec.loader.exec_module(tr)
    n = 0
    for s in tr.SLOT_NAMES:
        mk = tr.middle_edge_key(cube, s)
        lw, rw = tr.wing_keys_of_slot(cube, s)
        if mk is None or lw is None or rw is None:
            continue
        if sorted(mk) in (sorted(lw), sorted(rw)):
            continue
        n += 1
    return n


def base_commutators() -> List[Tuple[str, int, str]]:
    """[(axis, turns, outer_basis)] 组成 [slice, outer, slice', outer']。"""
    out = []
    for axis, turns in SLICE_ACTIONS:
        inv_turns = (4 - turns) % 4
        for o in OUTER_BASIS:
            inv_o = o[:-1] if o.endswith("'") else (o + "'" if not o.endswith("2") else o)
            # 处理 2 后缀（本 basis 无 2，忽略）
            out.append((axis, turns, o))
    return out


def run(seq: List) -> bool:
    c = Cube5.solved()
    apply_moveset(c, seq)
    centers_ok = centers_are_color_solved(c)
    fixed_ok = _fixed_centers_preserved(c)
    changed = mismatch_count(c) > 0
    return centers_ok, fixed_ok, changed, c


def main():
    found = []
    for axis, turns, o in base_commutators():
        inv_turns = (4 - turns) % 4
        inv_o = o[:-1] if o.endswith("'") else (o + "'")
        seq = [("SLICE", axis, turns), o, ("SLICE", axis, inv_turns), inv_o]
        centers_ok, fixed_ok, changed, c = run(seq)
        if centers_ok and fixed_ok and changed:
            found.append((axis, turns, o, mismatch_count(c)))
    print("base commutators preserving center+fixed AND changing assignment:")
    for f in found:
        print("  ", f)


if __name__ == "__main__":
    main()
