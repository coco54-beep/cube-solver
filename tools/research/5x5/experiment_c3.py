"""实验C3：两步 free-slice 批处理。
(1) gather：逐单元（W+outer^n+W'）提升目标关系，忽略中心(color_off 任意)。
(2) restore：在不拆对的前提下，用 2B B2 F2 2B'(整棱搬运宏) 等把已配棱搬出
    被中心还原动作搅动的带，再收缩中心 color_off 到 0，且保持 is_edge_paired。
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
from solver.edge5.state import is_edge_paired, centers_are_color_solved, center_color_off
from solver.edge5.compact_state import MOVES, state_of, step, color_off
from solver.edge5.free_slice import edge_relation, WHOLE_EDGE_SWAP_MAIN
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
                if rel > cur_rel:
                    cand = (rel, [w] + list(seq) + [wq], len(seq) + 2)
                    if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[2] < best[2]):
                        best = cand
    return best


def gather(cube5, target_slot, cap=2, max_it=10):
    w = cube5.clone()
    plan = []
    for it in range(max_it):
        if is_edge_paired(w, target_slot):
            return True, w, plan
        cur = edge_relation(state_of(w), target_slot).relation
        res = find_better(state_of(w), target_slot, cur, cap)
        if res is None:
            break
        rel, moves, _ = res
        for mv in moves:
            w.apply_move(mv)
        plan.append(moves)
    return is_edge_paired(w, target_slot), w, plan


def restore_keep_paired(cube5, target_slot, budget=400):
    """贪心收缩 color_off，保持 is_edge_paired 不被破坏。"""
    w = cube5.clone()
    steps = 0
    while center_color_off(w) > 0 and steps < budget:
        cur_co = center_color_off(w)
        best = None
        # 单/双层动作试探，选让 co 下降且不拆目标对的动作
        for mv in MOVES:
            m2 = w.clone()
            m2.apply_move(mv)
            if not is_edge_paired(m2, target_slot):
                continue
            co = center_color_off(m2)
            if co < cur_co:
                cand = (co, mv)
                if best is None or cand[0] < best[0]:
                    best = cand
        if best is None:
            break
        co, mv = best
        w.apply_move(mv)
        steps += 1
    return w, steps


def main():
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 11
    cap = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    rng = random.Random(seed)

    from solver.edge5.positions import SLOT_NAMES
    okg = 0
    okf = 0
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
        gok, wg, plan = gather(c, target, cap)
        okg += int(gok)
        if gok:
            wr, steps = restore_keep_paired(wg, target)
            fin = is_edge_paired(wr, target) and centers_are_color_solved(wr)
            okf += int(fin)
            print(f"case{i}: gather={'OK' if gok else 'X'} 单元{len(plan)}  restore={'OK' if fin else 'X'}(co={center_color_off(wr)})")
        else:
            print(f"case{i}: gather失败")
    print(f"gather {okg}/{total}  final(配+中心) {okf}/{total}")


if __name__ == "__main__":
    main()
