"""实验F：连续 free-slice 单条完整执行。
从真实中心已还原打乱 Cube5 出发，对目标棱执行：
   1. 选工作切片 W（能移动目标中棱的）。
   2. 打开 W，在打开态下枚举外层序列，把目标三块凑到带内工作槽（rel=3，带内）。
   3. 在打开态下用一个外层动作把整条组合搬到「非 W 带」的庇护槽。
   4. 关闭 W，验证目标棱 is_edge_paired 且 centers_are_color_solved。
   5. 真实 Cube5 重放。
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
from solver.edge5.compact_state import MOVES, state_of, step, MOVE_TABLES
from solver.edge5.free_slice import edge_relation, member_slots
from solver.edge5.positions import SLOT_NAMES
from solver.center5.legal_moves import invert_move_string

_OUTER = [m for m in MOVES if not m[:1].isdigit()]
_RWIDE = ("2U", "2D", "2L", "2R", "2F", "2B")
DEBUG = False

_MID = {mv: MOVE_TABLES[mv][0] for mv in MOVES}
_MIDX = {s: i for i, s in enumerate(SLOT_NAMES)}


def in_band(slot_name, w):
    return _MID[w][_MIDX[slot_name]] != _MIDX[slot_name]


def scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def find_pair_and_shelter(c, target):
    """在真实 c 上做 open->聚集->庇护->close；返回 (成功, 动作序列, 结束cube)。"""
    st0 = state_of(c)
    ms_pre, _, _ = member_slots(st0, target)
    w = next((x for x in _RWIDE if in_band(ms_pre, x)), None)
    if w is None:
        return False, [], c
    wq = invert_move_string(w)

    # 打开切片
    t = c.clone()
    t.apply_move(w)
    st_open = state_of(t)
    if DEBUG:
        ms0, wa0, wb0 = member_slots(st_open, target)
        print(f"    open {w}: 中槽={ms0} 翼a={wa0} 翼b={wb0}")
    # 打开态下找外层序列(<=2)使 rel==3 且组合带内
    best = None
    for n in [0, 1, 2]:
        for seq in product(_OUTER, repeat=n):
            st = st_open
            for mv in seq:
                st = step(st, mv)
            rel = edge_relation(st, target).relation
            if rel == 3:
                ms, wa, wb = member_slots(st, target)
                if in_band(ms, w):
                    best = (list(seq), ms)
                    break
        if best:
            break
    if best is None:
        if DEBUG:
            print("    凑近失败")
        return False, [], c
    seq, ms = best
    if DEBUG:
        print(f"    凑近 seq={' '.join(seq)} 组合槽={ms}")

    # 打开态下再找一个外层动作把组合搬到非 w 带槽
    st_after = st_open
    for mv in seq:
        st_after = step(st_after, mv)
    shelter_seq = None
    for mv in _OUTER:
        st2 = step(st_after, mv)
        if edge_relation(st2, target).relation == 3:
            ms2, _, _ = member_slots(st2, target)
            if not in_band(ms2, w):
                shelter_seq = (mv, ms2)
                break
    if shelter_seq is None:
        if DEBUG:
            print("    庇护失败(无外层可将组合搬出带)")
        return False, [], c
    shel_mv, shel_ms = shelter_seq
    if DEBUG:
        print(f"    庇护 mv={shel_mv} -> {shel_ms}")

    # 真实重放
    w_ = c.clone()
    plan = [w] + seq + [shel_mv] + [wq]
    for mv in plan:
        w_.apply_move(mv)
    # 按「同类型三块是否聚于同一槽」判定 assembled（而非槽名固定的 is_edge_paired）
    ms, wa, wb = member_slots(state_of(w_), target)
    g_ok = (ms == wa == wb) and ms is not None
    cc_ok = centers_are_color_solved(w_)
    if DEBUG:
        print(f"    gathered={g_ok} 槽={ms} centers_color_solved={cc_ok}")
    ok = g_ok and cc_ok
    return ok, plan, w_


def main():
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 11
    rng = random.Random(seed)

    global DEBUG
    DEBUG = len(sys.argv) > 4 and sys.argv[4] == "v"

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
        ok_, plan, w_ = find_pair_and_shelter(c, target)
        ok += int(ok_)
        if ok_:
            print(f"case{i}: 目标 {target}  OK  co={center_color_off(w_)}  计划 {' '.join(plan)}")
        else:
            print(f"case{i}: 目标 {target}  失败")
    print(f"连续free-slice单条 成功率 {ok}/{total}")


if __name__ == "__main__":
    main()
