"""实验B：验证「中棱+单翼」二块组合在保存（把组合搬出切片带）后、
切片恢复（W'）时不被撤销。

流程（free-slice 批处理单元）：
    W = 2U(打开切片)
    插入宏 A（建立目标组合）
    保存：外层动作把小组合搬出切片带
    W' = 2U'(关闭切片)
    验收：目标中+翼 仍在同一逻辑槽，且中心 color_off==0。

先在紧凑态枚举「保存动作」，再在真实 Cube5 上重放核实。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cube.cube5 import Cube5
from solver.edge5.compact_state import state_of, step, MOVES, MOVE_TABLES, _POS_HOME_SLOT, WING_ORDER, MIDDLE_ORDER
from solver.edge5.free_slice import edge_relation, member_slots, controlled_start
from solver.edge5.state import center_color_off, centers_are_color_solved

W = "2U"
WQ = "2U'"
INSERT_MACROS = {
    "2U_F'": {('2U'): ()},  # drop
}

# 插入宏各自的 A（去掉开头 W 与结尾 W'）。这里以 2U 家族为例。
INSERT_A = {
    ("2U", "F'", "U'", "F", "2U'"): ("F'", "U'", "F"),
    ("2U'", "F'", "U", "F", "2U"): ("U'", "F"),  # 2U' 开头的家族 W=2U'，此处暂不广化
}

_OUTER = [m for m in MOVES if not m[:1].isdigit()]

_pm = {mv: MOVE_TABLES[mv][0] for mv in MOVES}
_pw = {mv: MOVE_TABLES[mv][1] for mv in MOVES}
_pc = {mv: MOVE_TABLES[mv][2] for mv in MOVES}


def _ap(perm, mv, table):
    return tuple(perm[table[mv][j]] for j in range(len(perm)))


def _step(st, mv):
    return state_of.__self__ if False else None


# 用 real step
from solver.edge5.compact_state import step as real_step


def run(macro, target_slot, save_moves):
    """在紧凑态上执行：受控分散态 -> open W -> insert A -> save -> close W'。
    返回 (最终 edge_relation, 中心 color_off, 目标中/av槽)。"""
    start = controlled_start(target_slot, ( 3, 6, 3))  # 用一个近带入口
    # open
    st = real_step(start, W)
    # insert A
    for mv in INSERT_A[macro]:
        st = real_step(st, mv)
    # save: 外层动作
    for mv in save_moves:
        st = real_step(st, mv)
    # close
    st = real_step(st, WQ)
    rel = edge_relation(st, target_slot)
    from solver.edge5.compact_state import color_off
    co = color_off(st)
    ms, wa, wb = member_slots(st, target_slot)
    return rel, co, ms, wa, wb


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "UF"
    macro = sys.argv[2] if len(sys.argv) > 2 else "2U F' U' F 2U'"
    macro = tuple(macro.split())
    print("target", target, "macro", " ".join(macro), "W", W, "W'", WQ)
    # 枚举保存动作（外层 0/1/2 长），找出能保留组合且最后中心归面的
    from itertools import product
    best = []
    for slen in range(0, 3):
        for save in product(_OUTER, repeat=slen):
            try:
                rel, co, ms, wa, wb = run(macro, target, list(save))
            except KeyError:
                continue
            if co == 0 and rel.relation >= 2:  # 至少组合级且中心归面
                best.append((save, rel.relation, co, ms, wa, wb))
    best.sort(key=lambda t: (len(t[0]), -t[1]))
    print("成功保存(组合保留+中心归面)的保存动作数:", len(best))
    for save, rr, co, ms, wa, wb in best[:20]:
        print(f"  save {' '.join(save) if save else '(空)'}  relation={rr} co={co} 中槽={ms} 翼a槽={wa}")


if __name__ == "__main__":
    main()
