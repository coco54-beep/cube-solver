"""实验D：放宽的 open-slice 单元。
枚举 `W + outer^(1..N) + W'`，在受控分散态上找「单翼插入工作槽 +
关闭时中心 color_off==0 + 组合落到切片带外庇护槽」的单元。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from itertools import product
from solver.edge5.compact_state import MOVES, MOVE_TABLES, step, color_off
from solver.edge5.free_slice import edge_relation, member_slots, controlled_start
from solver.edge5.positions import SLOT_NAMES
from solver.center5.legal_moves import invert_move_string

_OUTER = [m for m in MOVES if not m[:1].isdigit()]
_WIDES = [m for m in MOVES if m[:1].isdigit()]

_MID = {mv: MOVE_TABLES[mv][0] for mv in MOVES}


def in_band(slot_name, w):
    return _MID[w][SLOT_NAMES.index(slot_name)] != SLOT_NAMES.index(slot_name)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "UF"
    maxN = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    print("target", target, "max outer len", maxN)
    ws = [w for w in _WIDES if in_band(target, w)]
    print("target 属于的切片带(宽层):", sorted(set(w for w in ws)))
    start = controlled_start(target, (3, 6, 6))

    found = []
    for w in _WIDES:
        for n in range(1, maxN + 1):
            for seq in product(_OUTER, repeat=n):
                st = step(start, w)
                for mv in seq:
                    st = step(st, mv)
                st = step(st, invert_move_string(w))
                rel = edge_relation(st, target)
                co = color_off(st)
                if co == 0 and rel.relation >= 2:
                    ms, wa, wb = member_slots(st, target)
                    # 组合槽应在 w 带外（庇护），即关闭后不再被 w 移动
                    sheltered = not in_band(ms, w)
                    found.append((rel.relation, ms, wa, wb, sheltered, [w] + list(seq) + [invert_move_string(w)], n))
    found.sort(key=lambda t: (-t[0], t[5], t[4]))
    print("找到(中心归面+关系>=2)单元数:", len(found))
    for f in found[:25]:
        rr, ms, wa, wb, shel, moves, n = f
        print(f"  rel={rr} 组合槽={ms} 庇护={shel} 长度{n}  {' '.join(moves)}")


if __name__ == "__main__":
    main()
