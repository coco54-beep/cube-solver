"""诊断：compact member_slots / edge_relation 是否与真实 is_edge_paired 一致。
在真实打乱+中心还原态、以及打开某些切片后的态，直接对比两者对目标棱的判定。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import random

from cube.cube5 import Cube5
from solver.center5 import solve_centers5
from solver.edge5.state import is_edge_paired, centers_are_color_solved
from solver.edge5.compact_state import state_of, step
from solver.edge5.free_slice import edge_relation, member_slots
from solver.edge5.positions import SLOT_NAMES

MOVES = ["U", "D", "L", "R", "F", "B", "U'", "D'", "L'", "R'", "F'", "B'",
         "U2", "D2", "L2", "R2", "F2", "B2",
         "2U", "2D", "2L", "2R", "2F", "2B",
         "2U'", "2D'", "2L'", "2R'", "2F'", "2B'",
         "2U2", "2D2", "2L2", "2R2", "2F2", "2B2"]


def scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    length = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    rng = random.Random(seed)
    c = Cube5.solved()
    scramble(c, length, rng)
    cr = solve_centers5(c)
    c.apply_moves(cr.moves)
    target = next((s for s in SLOT_NAMES if not is_edge_paired(c, s)), "UF")
    print("目标", target)

    for label, mv in [("closed-before", None)] + [(m, m) for m in MOVES]:
        t = c.clone()
        if mv:
            t.apply_move(mv)
        st = state_of(t)
        rel = edge_relation(st, target).relation
        ms, wa, wb = member_slots(st, target)
        real = is_edge_paired(t, target)
        # 对比 member_slots 与 real 的槽位是否一致
        print(f"{label:14s} comp_rel={rel} 中槽={ms} 翼a={wa} 翼b={wb}  real_paired={real}")
        if mv == "2R":
            break  # 先只看若干代表态


if __name__ == "__main__":
    main()
