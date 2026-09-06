"""高效搜索：找出 form `wide + outer_seq + wide'` 的中心保持（color_off==0）
且「非平凡翼动作」的 5x5 宏，分析其翼置换结构，找出可作保护式换翼原语的宏。

用纯置换表（不经 cube 对象）加速。
"""

import os
import sys
from collections import defaultdict
from itertools import product

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from solver.edge5.compact_state import MOVE_TABLES, CENTER_COLOR, MOVES

_OUTER = [m for m in MOVES if not m[:1].isdigit()]
_WIDE = [m for m in MOVES if m[:1].isdigit()]

_PM = {mv: MOVE_TABLES[mv][0] for mv in MOVES}
_PW = {mv: MOVE_TABLES[mv][1] for mv in MOVES}
_PC = {mv: MOVE_TABLES[mv][2] for mv in MOVES}


def _inv(mv):
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    return mv + "'"


def _apply_perm(perm, mv, table):
    return tuple(perm[table[mv][j]] for j in range(len(perm)))


def _wing_cycles(wp):
    vis = [False] * 24
    cycs = []
    for i in range(24):
        if not vis[i]:
            j = i
            l = []
            while not vis[j]:
                vis[j] = True
                l.append(j)
                j = wp[j]
            cycs.append(l)
    return cycs


def search(max_outer):
    start_w = tuple(range(24))
    start_m = tuple(range(12))
    start_c = tuple(range(54))
    found = []
    for w in _WIDE:
        wq = _inv(w)
        for A_len in range(1, max_outer + 1):
            for A in product(_OUTER, repeat=A_len):
                seq = (w,) + A + (wq,)
                wp = start_w
                mp = start_m
                cp = start_c
                for mv in seq:
                    wp = _apply_perm(wp, mv, _PW)
                    mp = _apply_perm(mp, mv, _PM)
                    cp = _apply_perm(cp, mv, _PC)
                off = sum(1 for j, v in enumerate(cp) if CENTER_COLOR[v] != CENTER_COLOR[j])
                if off != 0:
                    continue
                if wp == start_w:
                    continue
                # 只保留「中棱不动」的：即 middle 恒等 -> 翼可独立于中棱交换
                if mp != start_m:
                    continue
                cycs = _wing_cycles(wp)
                found.append((seq, wp, cycs))
    return found


def main():
    max_outer = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    found = search(max_outer)
    print(f"候选数={len(found)}")
    # 按翼循环结构统计
    struct = defaultdict(int)
    for _s, _wp, cycs in found:
        lens = sorted(len(c) for c in cycs)
        struct[tuple(lens)] += 1
    # 最想要的：2-cycle 主导（多个对换），即一条 2 元循环很多
    def key_count(lens):
        return sum(1 for l in lens if l == 2)
    best = sorted(struct.items(), key=lambda kv: -key_count(kv[0]))[:15]
    print("最具'翼对换'倾向的循环结构（2-cycle 数由高到低）：")
    for lens, cnt in best:
        print(f"  cyc={lens}  count={cnt}")
    # 展示几条最长 2-cycle 的宏
    best_by_cycles = sorted(found, key=lambda t: -sum(1 for c in t[2] if len(c) == 2))[:10]
    print("示例宏（2-cycle 数最多）：")
    for seq, wp, cycs in best_by_cycles:
        n2 = sum(1 for c in cycs if len(c) == 2)
        print(f"  {' '.join(seq)}  2-cycles={n2}  cycles={sorted(len(c) for c in cycs)}")


if __name__ == "__main__":
    main()
