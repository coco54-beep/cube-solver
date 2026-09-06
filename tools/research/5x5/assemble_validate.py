"""受控验证：free-slice 宏通过「外层 setup + 宏 + 逆 setup」在真实
中心已还原打乱 Cube5 上组装目标整条棱。

搜索用紧凑状态加速；命中后只在真实 Cube5 上重放校验。
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
from solver.edge5.state import is_edge_paired, paired_count, centers_are_color_solved
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

_pm = {mv: MOVE_TABLES[mv][0] for mv in MOVES}
_pw = {mv: MOVE_TABLES[mv][1] for mv in MOVES}
_pc = {mv: MOVE_TABLES[mv][2] for mv in MOVES}


def _ap(perm, mv, table):
    return tuple(perm[table[mv][j]] for j in range(len(perm)))


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


def find_assembly(start_compact, target_slot, cap):
    """紧凑搜索：逐 setup(外层) + 各宏，看目标槽 relation 是否到 3。"""
    for ss_len in range(0, cap + 1):
        for setup in product(_OUTER, repeat=ss_len):
            # 计算 setup 后的 compact 态
            st = start_compact
            for mv in setup:
                st = step(st, mv)
            for macro in MACROS:
                s2 = st
                for mv in macro:
                    s2 = step(s2, mv)
                for mv in inv_seq(setup):
                    s2 = step(s2, mv)
                if edge_relation(s2, target_slot).relation == 3:
                    return (list(setup), list(macro))
    return None


def main():
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    cap = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    rng = random.Random(seed)

    from solver.edge5.positions import SLOT_NAMES
    overall = 0
    ok = 0
    for i in range(n):
        c = Cube5.solved()
        scramble(c, length, rng)
        cr = solve_centers5(c)
        c.apply_moves(cr.moves)
        assert centers_are_color_solved(c)
        target = next((s for s in SLOT_NAMES if not is_edge_paired(c, s)), None)
        if target is None:
            print(f"case{i}: 中心后已全配对")
            ok += 1
            overall += 1
            continue
        overall += 1
        before = paired_count(c)
        res = find_assembly(state_of(c), target, cap)
        if res:
            setup, macro = res
            # 真实重放校验
            w = c.clone()
            for mv in setup:
                w.apply_move(mv)
            for mv in macro:
                w.apply_move(mv)
            for mv in inv_seq(setup):
                w.apply_move(mv)
            paired = is_edge_paired(w, target)
            after = paired_count(w)
            html = "PAIRED" if paired else "NOT-PAIRED"
            if paired:
                ok += 1
            print(f"case{i}: {target} -> {html}  setup {' '.join(setup)} | 宏 {' '.join(macro)}  paired {before}->{after}")
        else:
            print(f"case{i}: {target} 组装失败 (cap={cap})")
    print(f"组装成功率(真实) {ok}/{overall}")


if __name__ == "__main__":
    main()
