"""探测 5x5 保护式换棱原语（M3 关键前提）。

目标：从 solved 出发，找短序列，使结果满足：
  1) center color_off == 0（中心按颜色归面）
  2) 所有 12 条逻辑棱保持「3 成员色对连贯」——即每个槽 3 块色对一致，
     这样"已配对组"会作为整体被搬移、不被拆散
  3) 对翼的作用显著（wing 置换非平凡），且最好是可共轭成"交换两翼位"型
  （wing 置换是 2-cycle 或 U 层 4 组轮换型）

候选形态：单个宽层动作（如 2R）夹带若干外层动作，再以宽层逆收尾。
本实验只做探测，不做运行时依赖。
"""

import os
import sys
import time
from collections import Counter

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from itertools import product

from cube.cube5 import Cube5

from solver.edge5.compact_state import (
    MOVES,
    color_off,
    state_of,
    step,
)
from solver.edge5.positions import (
    MIDDLE_ORDER,
    WING_ORDER,
    COORD_TO_SLOT,
    slot,
)
from solver.edge5.compact_state import MOVE_TABLES

_OUTER = [m for m in MOVES if not m[:1].isdigit()]
_WIDE = [m for m in MOVES if m[:1].isdigit()]


def _inv(mv):
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    return mv + "'"


# 用 action 置换表快速评价：给定 action 序列，返回 (center_off, wing_perm, mid_perm)
_PM = {mv: MOVE_TABLES[mv][0] for mv in MOVES}
_PW = {mv: MOVE_TABLES[mv][1] for mv in MOVES}
_PC = {mv: MOVE_TABLES[mv][2] for mv in MOVES}


def _apply(state, mv):
    return (tuple(state[0][_PM[mv][j]] for j in range(12)),
            tuple(state[1][_PW[mv][j]] for j in range(24)),
            tuple(state[2][_PC[mv][j]] for j in range(54)))


def _color_off_from_center(center_perm):
    from solver.edge5.compact_state import CENTER_COLOR
    return sum(1 for j, v in enumerate(center_perm) if CENTER_COLOR[v] != CENTER_COLOR[j])


def _wingspace(mid_perm, wing_perm):
    """判断所有 12 条逻辑棱是否保持「3 成员连贯且整体轮换」。

    对每条 home 逻辑棱 s：其中棱 home 槽 s、两翼 home 槽 s；
    经置换后中棱移到槽 ms、两翼也移到槽 ms（同一槽），且 s->ms 是槽间双射。
    这样"每个棱组"作为整体搬移，已配对组不被拆散。
    """
    mslot = [COORD_TO_SLOT[MIDDLE_ORDER[mid_perm[j]]] for j in range(12)]
    wslot = [COORD_TO_SLOT[WING_ORDER[wing_perm[w]]] for w in range(24)]
    # 每条 home 槽：其中棱槽 + 两翼槽
    home_of_mid = [COORD_TO_SLOT[MIDDLE_ORDER[j]] for j in range(12)]
    home_of_wing = [COORD_TO_SLOT[WING_ORDER[w]] for w in range(24)]
    group = {}
    for j in range(12):
        group.setdefault(home_of_mid[j], set()).add(mslot[j])
    for w in range(24):
        group.setdefault(home_of_wing[w], set()).add(wslot[w])
    # 每个 home 槽必须映射到单一当前槽
    if any(len(v) != 1 for v in group.values()):
        return False
    vals = [next(iter(v)) for v in group.values()]
    # 12 条棱必须映射到 12 个不同槽（双射）
    return len(vals) == 12 and len(set(vals)) == 12


def search(max_outer=2):
    start = (tuple(range(12)), tuple(range(24)), tuple(range(54)))
    results = []
    # 形态：宽层 W, 外层序列 A, W 的逆
    for w in _WIDE:
        wq = _inv(w)
        for A_len in range(0, max_outer + 1):
            for A in product(_OUTER, repeat=A_len):
                seq = (w,) + A + (wq,)
                st = start
                for mv in seq:
                    st = _apply(st, mv)
                co = _color_off_from_center(st[2])
                if co != 0:
                    continue
                if not _wingspace(st[0], st[1]):
                    continue
                # 记录 wing 置换（从列表转元组）
                wing_perm = st[1]
                results.append((seq, wing_perm))
    return results


def main():
    max_outer = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    t0 = time.time()
    results = search(max_outer)
    print(f"原语候选数={len(results)} 耗时{time.time()-t0:.1f}s")
    # 按 wing 置换类型分组统计
    byperm = Counter(r[1] for r in results)
    print("不同 wing 置换种类数:", len(byperm))
    # 展示每种 wing 置换的第一条候选（长度最短）
    seen = {}
    for seq, wp in results:
        if wp not in seen or len(seq) < len(seen[wp][0]):
            seen[wp] = (seq, wp)
    for wp, (seq, _wp) in sorted(seen.items(), key=lambda kv: len(kv[1][0]))[:20]:
        # 简单描述：2-cycle 数
        # 计算循环数
        vis = [False]*24; cyc=0
        for i in range(24):
            if not vis[i]:
                j=i; l=0
                while not vis[j]:
                    vis[j]=True; j=wp[j]; l+=1
                cyc+=1
        print(f"  宏{' '.join(seq)}  翼循环数={cyc}")
    # 统计 2-cycle 型的宏
    two = [r for r in results if sum(1 for i in range(24) if r[1][i]==i) >= 22]
    print("近似单转移（≥22 个翼位固定）的宏数:", len(two))


if __name__ == "__main__":
    main()
