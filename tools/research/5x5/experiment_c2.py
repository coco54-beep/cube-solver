"""实验C2：用 open-slice 单元（W + outer^n + W'）在真实中心已还原打乱 Cube5 上
迭代提升目标棱关系等级，直到 is_edge_paired。
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
from solver.edge5.compact_state import MOVES, state_of, step, color_off
from solver.edge5.free_slice import edge_relation
from solver.center5.legal_moves import invert_move_string

_OUTER = [m for m in MOVES if not m[:1].isdigit()]
_WIDES = [m for m in MOVES if m[:1].isdigit()]


def scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def find_better(st_compact, target_slot, cur_rel, cap):
    best = None
    for w in _WIDES:
        wq = invert_move_string(w)
        for n in range(0, cap + 1):
            for seq in product(_OUTER, repeat=n):
                st = step(st_compact, w)
                for mv in seq:
                    st = step(st, mv)
                st = step(st, wq)
                rel = edge_relation(st, target_slot).relation
                co = color_off(st)
                if co != 0:
                    continue
                if rel > cur_rel:
                    cand = (rel, [w] + list(seq) + [wq], len(seq) + 2)
                    if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[2] < best[2]):
                        best = cand
    return best


def assemble(cube5, target_slot, cap=2, max_it=8):
    w = cube5.clone()
    for it in range(max_it):
        if is_edge_paired(w, target_slot):
            return True, it
        cur = edge_relation(state_of(w), target_slot).relation
        res = find_better(state_of(w), target_slot, cur, cap)
        if res is None:
            return is_edge_paired(w, target_slot), it
        rel, moves, _ = res
        for mv in moves:
            w.apply_move(mv)
    return is_edge_paired(w, target_slot), max_it


def main():
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
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
