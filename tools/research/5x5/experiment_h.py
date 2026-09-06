"""实验H：验证「加入纯内层切片动作(3X)后 free-slice 才可行」。
从真实中心已还原打乱 Cube5 出发，在真实 Cube 上做有限深度 BFS，
动作集含外层+宽层+内层切片(3X)，用 type-anchored(member_slots 三块同槽) 验收。
看加入 3X 后能否把目标三块聚到同一槽。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import random

from cube.cube5 import Cube5
from solver.center5 import solve_centers5
from solver.edge5.state import centers_are_color_solved
from solver.edge5.compact_state import state_of
from solver.edge5.free_slice import member_slots
from solver.edge5.positions import SLOT_NAMES

MOVES = ["U", "D", "L", "R", "F", "B", "U'", "D'", "L'", "R'", "F'", "B'",
         "2U", "2D", "2L", "2R", "2F", "2B", "2U'", "2D'", "2L'", "2R'", "2F'", "2B'"]
INNER = ["3U", "3D", "3L", "3R", "3F", "3B", "3U'", "3D'", "3L'", "3R'", "3F'", "3B'"]


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
    return ms is not None and ms == wa == wb


def combo(members):
    ms, wa, wb = members
    return ms is not None and (wa == ms or wb == ms)


def main():
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 11
    maxd = int(sys.argv[4]) if len(sys.argv) > 4 else 4
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
        target = None
        for s in SLOT_NAMES:
            if not gathered(member_slots(state_of(c), s)):
                target = s
                break
        if target is None:
            continue
        total += 1
        # 深度有限 BFS，含 INNER 动作
        from collections import deque
        start = c.clone()
        q = deque([(start, 0, [])])
        best_m = None
        best_moves = []
        seen = set()
        while q:
            node, d, path = q.popleft()
            if d > maxd:
                continue
            mem = member_slots(state_of(node), target)
            if gathered(mem):
                best_m = mem
                best_moves = path
                break
            if combo(mem) and best_m is None:
                best_m = mem
                best_moves = path
            for mv in INNER:
                nn = node.clone()
                nn.apply_move(mv)
                q.append((nn, d + 1, path + [mv]))
        if best_m is not None:
            ok_combo += 1
            if gathered(best_m):
                ok_full += 1
            print(f"case{i}: {target} -> {'GROUP' if gathered(best_m) else 'COMBO'} 中={best_m[0]}/{best_m[1]}/{best_m[2]} 深度{len(best_moves)}")
        else:
            print(f"case{i}: {target} 内层切片 BFS(d={maxd}) 无改善")
    print(f"combo {ok_combo}/{total}  full {ok_full}/{total}")


if __name__ == "__main__":
    main()
