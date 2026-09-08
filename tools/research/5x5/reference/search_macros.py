"""搜索「宏结束中心恢复、改变中棱↔翼相对归属」的候选宏（Gate 5c / Plan 3）。

基础结构：
- 一级：`[A, B] = A B A' B'`，A 为内层切片或宽层动作，B 为外层短序列（1~3 步）。
- 二级：共轭 `X [A, B] X'`（X 外层 setup）—— 由上一层筛出的有效宏再共轭。
- 三级：两段式 `C1 C2` 组合恢复中心。

用 `MacroEffect` 在复原态计算完整效果并筛选（Plan 4）：
保留 中心恢复 + 非整体搬槽（中棱或单侧翼产生 3-cycle）的候选。

`python search_macros.py` 直接运行。
"""
from __future__ import annotations

import itertools
import os
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from macro_effect import compute_effect, MacroEffect

SLICE = ["M", "M'", "M2", "E", "E'", "E2", "S", "S'", "S2"]
WIDE = ["2R", "2R'", "2L", "2L'", "2U", "2U'", "2D", "2D'", "2F", "2F'", "2B", "2B'"]
OUTER = ["R", "R'", "U", "U'", "F", "F'", "L", "L'", "D", "D'", "B", "B'"]


def inv_token(t):
    if t.endswith("'"):
        return t[:-1]
    if t.endswith("2"):
        return t
    return t + "'"


def m3(e: MacroEffect) -> bool:
    return "3" in [str(len(c)) for c in e.middle_cycles()] or any(len(c) >= 2 for c in e.middle_cycles())


def filter_good(e: MacroEffect) -> bool:
    """筛选：中心恢复 + 固定面心 + 非整体搬槽 + 影响槽数<=6 + 至少一个中棱cycle。"""
    if not (e.centers_ok and e.fixed_centers_ok):
        return False
    if e.moves_whole_slots():
        return False
    if len(e.affected_slots) > 6:
        return False
    if not e.middle_cycles():
        return False
    return True


def main():
    from macro_effect import compute_effect
    good = []
    sl = SLICE + WIDE
    # 一级：B 为单步外层
    for a in sl:
        for b in OUTER:
            seq = [a, b, inv_token(a), inv_token(b)]
            e = compute_effect(seq)
            if e.moves_whole_slots():
                continue
            if filter_good(e):
                good.append(seq)
    # 一级：B 为两步外层
    for a in sl:
        for b1, b2 in itertools.product(OUTER, repeat=2):
            seq = [a, b1, b2, inv_token(a), inv_token(b2), inv_token(b1)]
            e = compute_effect(seq)
            if e.moves_whole_slots():
                continue
            if filter_good(e):
                good.append(seq)
    print(f"一级候选（中心恢复+非整体搬+中棱cycle）共 {len(good)}")
    for g in good[:50]:
        e = compute_effect(g)
        print("  ", "".join(g), "mid:", e.middle_cycles(), "lw:", e.left_wing_cycles(),
              "rw:", e.right_wing_cycles(), "slots:", len(e.affected_slots))


if __name__ == "__main__":
    main()
