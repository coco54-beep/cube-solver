"""直接验证 compact step 与真实 Cube5 apply_move 是否对同一序列一致。
对一序列 seq，从同一打乱态： (a) 用 compact step 连乘算出 compact 态；
(b) 用真实 cube apply 得到真实态再 state_of。对比两者 member_slots（按类型追踪）。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import random

from cube.cube5 import Cube5
from solver.edge5.compact_state import state_of, step
from solver.edge5.free_slice import member_slots, edge_relation
from solver.edge5.positions import SLOT_NAMES

MOVES = ["U", "D", "L", "R", "F", "B", "U'", "D'", "L'", "R'", "F'", "B'",
         "2U", "2D", "2L", "2R", "2F", "2B", "2U'", "2D'", "2L'", "2R'", "2F'", "2B'"]


def scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def main():
    rng = random.Random(3)
    c = Cube5.solved()
    scramble(c, 4, rng)
    st0 = state_of(c)
    seq = ["2R", "F", "2R'"]
    # compact 连乘
    st_c = st0
    for mv in seq:
        st_c = step(st_c, mv)
    # 真实
    r = c.clone()
    for mv in seq:
        r.apply_move(mv)
    st_r = state_of(r)
    # 对比每个目标类型的 member_slots
    for t in SLOT_NAMES:
        mc = member_slots(st_c, t)
        mr = member_slots(st_r, t)
        if mc != mr:
            print(f"MISMATCH {t}: compact={mc} real={mr}")

    # 广化对比：对大量随机序列，找 compact/real 分歧
    print("--- 随机序列测试 ---")
    for trial in range(300):
        cs = Cube5.solved()
        scramble(cs, 5, rng)
        s0 = state_of(cs)
        seq = [rng.choice(MOVES) for _ in range(rng.randint(1, 6))]
        sc = s0
        for mv in seq: sc = step(sc, mv)
        rr = cs.clone()
        for mv in seq: rr.apply_move(mv)
        sr = state_of(rr)
        for t in SLOT_NAMES:
            if member_slots(sc, t) != member_slots(sr, t):
                print(f"trial{trial} sequence {' '.join(seq)} -> MISMATCH {t}")
                break
    print("done")


if __name__ == "__main__":
    main()
