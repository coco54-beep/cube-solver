"""实验G：连续 free-slice 插入。
打开工作切片 W 后保持不关，在打开态下枚举外层序列，把目标中棱某翼
送入目标中棱所在槽（类型锚定：member_slots 三块同槽/同槽两块的判定）。
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
from solver.edge5.state import centers_are_color_solved
from solver.edge5.compact_state import MOVES, state_of, step
from solver.edge5.free_slice import member_slots
from solver.edge5.positions import SLOT_NAMES

_OUTER = [m for m in MOVES if not m[:1].isdigit()]

MOVES = ["U", "D", "L", "R", "F", "B", "U'", "D'", "L'", "R'", "F'", "B'",
         "2U", "2D", "2L", "2R", "2F", "2B", "2U'", "2D'", "2L'", "2R'", "2F'", "2B'",
         "2U2", "2D2", "2L2", "2R2", "2F2", "2B2"]


def scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def gathered(members):
    ms, wa, wb = members
    return (ms == wa == wb and ms is not None)


def combo(members):
    ms, wa, wb = members
    return (ms is not None and (wa == ms or wb == ms))


def main():
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 11
    rng = random.Random(seed)

    ok_combo = 0
    ok_full = 0
    total = 0
    for i in range(n):
        c = Cube5.solved()
        scramble(c, length, rng)
        cr = solve_centers5(c)
        c.apply_moves(cr.moves)
        assert centers_are_color_solved(c)
        # 选一个「类型三块分散」的目标
        target = None
        for s in SLOT_NAMES:
            if not gathered(member_slots(state_of(c), s)):
                target = s
                break
        if target is None:
            print(f"case{i}: 全聚集")
            continue
        total += 1
        m0 = member_slots(state_of(c), target)
        # 对每个宽层作为打开切片，在打开态枚举外层(<=2)
        done = False
        for w in ("2U", "2D", "2L", "2R", "2F", "2B"):
            t = c.clone()
            t.apply_move(w)
            st_open = state_of(t)
            for nseq in [1, 2]:
                for seq in product(_OUTER, repeat=nseq):
                    st = st_open
                    for mv in seq:
                        st = step(st, mv)
                    mem = member_slots(st, target)
                    if combo(mem):
                        ok_combo += 1
                        if gathered(mem):
                            ok_full += 1
                        print(f"case{i}: {target} 打开{w} 序列{' '.join(seq)} -> 中={mem[0]} 翼a={mem[1]} 翼b={mem[2]} {'GROUP' if gathered(mem) else 'COMBO'}")
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if not done:
            print(f"case{i}: {target} 打开切片+外层序列 无改善 (初始中={m0[0]} a={m0[1]} b={m0[2]})")
    print(f"combo 命中 {ok_combo}/{total}  full 命中 {ok_full}/{total}")


if __name__ == "__main__":
    main()
