"""实验C：迭代式 free-slice 组装——对目标棱反复执行
「外层 setup + 宏 + 逆setup」以提升关系等级，直到 is_edge_paired。

搜索用紧凑态加速（找出能提升关系等级的 setup+宏），命中后在真实 Cube5 上应用。
测量：对中心已还原打乱 Cube5，能否把目标棱从分散组装为完整配对。
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
from solver.edge5.state import is_edge_paired, centers_are_color_solved, center_color_off, paired_count
from solver.edge5.compact_state import MOVES, state_of, step, MOVE_TABLES
from solver.edge5.free_slice import edge_relation
from solver.center5.legal_moves import invert_move_string

_OUTER = [m for m in MOVES if not m[:1].isdigit()]

MACROS = [
    ("2L", "D", "R'", "D'", "2L'"),
    ("2L'", "U", "R", "U'", "2L"),
    ("2L2", "B", "R2", "B'", "2L2"),
    ("2U", "F'", "U'", "F", "2U'"),
    ("2U'", "F'", "U", "F", "2U"),
    ("2U2", "F'", "U2", "F", "2U2"),
]


def inv_seq(seq):
    return [invert_move_string(m) for m in reversed(seq)]


def scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def find_better(st_compact, target_slot, cur_rel, cap):
    """在紧凑态上找能提升目标关系等级的 (setup, macro)。"""
    best = None
    for ss_len in range(0, cap + 1):
        for setup in product(_OUTER, repeat=ss_len):
            st = st_compact
            for mv in setup:
                st = step(st, mv)
            for macro in MACROS:
                s2 = st
                for mv in macro:
                    s2 = step(s2, mv)
                for mv in inv_seq(setup):
                    s2 = step(s2, mv)
                rel = edge_relation(s2, target_slot).relation
                if rel > cur_rel:
                    cand = (rel, list(setup), list(macro), len(setup))
                    if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[3] < best[3]):
                        best = cand
        if best is not None:
            return best
    return None


def assemble(cube5, target_slot, cap=2, max_it=6):
    """在真实 cube5 状态基础上迭代组装目标棱；返回 (是否配对, 步数)。"""
    w = cube5.clone()
    for it in range(max_it):
        if is_edge_paired(w, target_slot):
            return True, it
        st = state_of(w)
        cur = edge_relation(st, target_slot).relation
        res = find_better(st, target_slot, cur, cap)
        if res is None:
            return False, it
        rel, setup, macro, _ = res
        for mv in setup:
            w.apply_move(mv)
        for mv in macro:
            w.apply_move(mv)
        for mv in inv_seq(setup):
            w.apply_move(mv)
    return is_edge_paired(w, target_slot), max_it


def main():
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 11
    cap = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    rng = random.Random(seed)

    from solver.edge5.positions import SLOT_NAMES
    ok = 0
    total = 0
    for i in range(n):
        c = Cube5.solved()
        scramble(c, length, rng)
        cr = solve_centers5(c)
        c.apply_moves(cr.moves)
        assert centers_are_color_solved(c)
        target = next((s for s in SLOT_NAMES if not is_edge_paired(c, s)), None)
        if target is None:
            print(f"case{i}: 中心后全配对")
            continue
        total += 1
        ok_it, it = assemble(c, target, cap)
        ok += int(ok_it)
        print(f"case{i}: 目标 {target}  {'PAIRED' if ok_it else 'NOT-PAIRED'}  迭代 {it} 次")
    print(f"组装成功率 {ok}/{total}")


if __name__ == "__main__":
    main()
