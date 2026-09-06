"""实验E：连续 free-slice 核心验证。

给定工作切片 W，在「打开切片后保持不关」的状态下，枚举连续外层插入序列，
把目标翼送入中棱所在工作槽（提升关系），并检查：
  - 组合是否落入 W 带内某个工作槽；
  - 是否能用单个外层动作把该组合整体搬出 W 带（暂存到非带槽）；
最后在真实 Cube5 上重放。

思路：真正连续 free-slice 不逐个闭环，而是在打开态下连续用外层动作
「丢翼进带、凑到中棱槽、整棱搬出」。本实验先验证「丢翼进带 + 凑到中棱槽」。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import random
from itertools import product

from cube.cube5 import Cube5
from solver.center5 import solve_centers5
from solver.edge5.state import is_edge_paired, centers_are_color_solved
from solver.edge5.compact_state import MOVES, state_of, step, MOVE_TABLES, color_off
from solver.edge5.free_slice import edge_relation, member_slots
from solver.edge5.positions import SLOT_NAMES
from solver.center5.legal_moves import invert_move_string

_OUTER = [m for m in MOVES if not m[:1].isdigit()]
# 目标棱 UF 的工作切片：选能让翼进带的。用 2U 作代表
WORK_W = "2U"

_MID = {mv: MOVE_TABLES[mv][0] for mv in MOVES}


def in_band(slot_name, w):
    return _MID[w][SLOT_NAMES.index(slot_name)] != SLOT_NAMES.index(slot_name)


def scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def enum_insert(st_open, target_slot, n):
    """打开态 st_open 下，枚举外层序列，返回 (rel, seq, 中槽, 翼a槽)的组合。"""
    results = []
    for seq in product(_OUTER, repeat=n):
        st = st_open
        for mv in seq:
            st = step(st, mv)
        rel = edge_relation(st, target_slot)
        if rel.relation >= 2:
            ms, wa, wb = member_slots(st, target_slot)
            results.append((rel.relation, ms, wa, wb, list(seq)))
    return results


def main():
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    rng = random.Random(seed)

    c = Cube5.solved()
    scramble(c, length, rng)
    cr = solve_centers5(c)
    c.apply_moves(cr.moves)
    assert centers_are_color_solved(c)

    target = next((s for s in SLOT_NAMES if not is_edge_paired(c, s)), "UF")
    # 目标中棱在中心已还原态的位置
    ms_pre, _, _ = member_slots(state_of(c), target)
    # 选择能移动目标中棱槽的切片作工作切片
    cand = [w for w in ("2U", "2D", "2L", "2R", "2F", "2B") if in_band(ms_pre, w)]
    WORK_W = cand[0] if cand else "2U"
    print("目标", target, " 中棱当前槽", ms_pre, " 工作切片", WORK_W)

    # 打开切片
    c.apply_move(WORK_W)
    st_open = state_of(c)
    # 目标中棱在打开态的位置
    ms0, wa0, wb0 = member_slots(st_open, target)
    print("打开后 目标中槽", ms0, " 翼a槽", wa0, " 翼b槽", wb0)

    # 枚举外层插入(长度1~3)，找关系>=2
    for n in [1, 2, 3]:
        res = enum_insert(st_open, target, n)
        if res:
            by_rel = {}
            for rr, ms, wa, wb, seq in res:
                by_rel.setdefault(rr, []).append((ms, wa, wb, seq))
            print(f"n={n}: 达到 {sorted(by_rel, reverse=True)[0]} 级 共{len(res)}条 (最高示例):")
            for ms, wa, wb, seq in by_rel[max(by_rel)][:6]:
                inband = in_band(ms, WORK_W)
                print(f"    rel={max(by_rel)} 中槽={ms} 带内={inband}  序列={' '.join(seq)}")
        else:
            print(f"n={n}: 无提升")


if __name__ == "__main__":
    main()
