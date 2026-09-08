"""联合归属求解器（joint_solver.py）
在「中心归面 + 翼对已配置(pairing5)」基础上，把每个槽内容物看作三元组（中棱+翼对），
用整体搬运宏（mid_map==wing_map 的外层共轭 3-cycle，whole-slot transport）+ 纯中棱
3-cycle 宏做目标为「所有槽 (mid_home,wing_home)==(slot,slot)」（abstract identity）
的求解。

核心模型（key correction 后的正确模型）：
- transport 宏：同时 3-cycle 中棱归属与翼对归属（mid_map==wing_map），
  保持「中棱+翼对」联合奇偶不变。
- 中棱宏：只动中棱（wing_map==identity）。

【重要实测修正（相对旧 premise）】
基于 group 分析 + 实测，求解到 abstract identity 的**必要**条件是：
- wing（左翼）置换必须能被 transport 宏（均为偶 3-cycle）归位 → wing 必须为**偶**置换，
  且落在 transport 宏生成的子群内；以及
- **mid 置换必须为偶**（因为只有 transport（偶）与中棱宏（偶）作用 mid，凡作用 mid 的
  宏均为偶 → 若 mid 初始为奇，则永远无法到 id）。

因此正确分区为：
- seed19: mid=e wing=e        → 偶宏可解（two-phase 实测 identity 达成）。
- seed23/seed4: mid=e wing=o  → wing 奇，需奇 wing parity 宏（已找到），但单次 2-cycle
  不足以让 wing 落入 transport 子群，需联合搜索。
- seed2/seed51/seed7: 均 **mid 奇**（seed2/51 mid=o wing=o；seed7 mid=o wing=e）
  → mid 奇无法被现有偶宏归位，需要「奇 mid parity 宏」，尚未找到。

本模块提供：
- 抽象求解 two-phase（transport 解翼对，再中棱宏解中棱）。
- parity 宏收集（奇 wing 2-cycle，centers_ok & fixed_centers_ok）。
- solve_joint()：结合 parity 尝试；返回 (ok, macro_seq, note)。
- 对达 identity 的 fixture 做真实回放并统计 VALID / 朝向。
"""
from __future__ import annotations

import os
import sys
import json
import itertools
import importlib.util
import time
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, r"D:\coco\cube-solver")
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def load(name, path):
    sys.modules[name] = None
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


REF = r"D:\coco\cube-solver\tools\research\5x5\reference"
ts = load("ts", REF + r"\terminal_state.py")
p5 = load("p5", REF + r"\pairing5.py")
me = load("me", REF + r"\macro_effect.py")
ml = load("ml", REF + r"\macro_lib.py")
ms = load("ms", REF + r"\terminal_solver.py")

from cube.cube5 import Cube5  # noqa: E402

N = 12
GATE5B = r"D:\coco\cube-solver\tests\fixtures\edge5\gate5b"


def fixture(name) -> Cube5:
    with open(os.path.join(GATE5B, name), encoding="utf-8") as f:
        fx = json.load(f)
    c = Cube5.solved()
    for k in ["scramble", "center_moves", "gate3_moves", "gate4_moves",
              "setup_moves", "insert_moves"]:
        if k in fx:
            c.apply_moves(fx[k])
    return c


def perm_sign(perm, n=N) -> int:
    seen = [False] * n
    s = 1
    for i in range(n):
        if not seen[i]:
            j = i
            cyc = 0
            while not seen[j]:
                seen[j] = True
                j = perm[j]
                cyc += 1
            if cyc % 2 == 0:
                s = -s
    return s


# --------------------------------------------------------------------------
# 宏集
# --------------------------------------------------------------------------

def build_transport_and_middle() -> Tuple[List[ms.Macro], List[ms.Macro], List[Tuple], List[Tuple]]:
    macros = ms.build_all_macros()
    trans = [m for m in macros if tuple(m.mid_map) == tuple(m.wing_map)]
    mid_only = [m for m in macros if tuple(m.wing_map) == tuple(range(N))]
    tmaps = [tuple(m.mid_map) for m in trans]
    mmaps = [tuple(m.mid_map) for m in mid_only]
    return trans, mid_only, tmaps, mmaps


def collect_lw_odd_parity(max_outer_len=3) -> List[ms.Macro]:
    """奇左翼 2-cycle parity 宏：WIDE commutator，保 center & fixed，mid 不动，lw 单 2-cycle。"""
    WIDE = ["2R", "2R'", "2L", "2L'", "2U", "2U'", "2D", "2D'",
            "2F", "2F'", "2B", "2B'"]
    OUTER = ["R", "R'", "U", "U'", "F", "F'", "L", "L'", "D", "D'", "B", "B'"]

    def it(t):
        if t.endswith("'"):
            return t[:-1]
        if t.endswith("2"):
            return t
        return t + "'"

    out = []
    seen = set()
    for a in WIDE:
        ia = it(a)
        for L in range(1, max_outer_len + 1):
            for combo in itertools.product(OUTER, repeat=L):
                seq = ml._compress([a] + list(combo) + [ia] + [it(x) for x in reversed(combo)])
                k = tuple(seq)
                if k in seen:
                    continue
                seen.add(k)
                eff = me.compute_effect(seq)
                if not (eff.centers_ok and eff.fixed_centers_ok):
                    continue
                if eff.moves_whole_slots():
                    continue
                if eff.middle_cycles():
                    continue
                cyc = eff.left_wing_cycles()
                if len(cyc) != 1 or len(cyc[0]) != 2:
                    continue
                out.append(ms.Macro(
                    "PAR:" + "".join(seq), seq,
                    ms._map_from_perm(eff.middle_perm),
                    ms._map_from_perm(eff.left_wing_perm),
                    ms._flip_src_of(eff.middle_flip, eff.middle_perm),
                    ms._flip_src_of(eff.left_flip, eff.left_wing_perm)))
    return out


def collect_rw_odd_parity(max_outer_len=3) -> List[ms.Macro]:
    """奇右翼 2-cycle parity 宏（抽象里不跟踪右翼，但作为参考）。"""
    WIDE = ["2R", "2R'", "2L", "2L'", "2U", "2U'", "2D", "2D'",
            "2F", "2F'", "2B", "2B'"]
    OUTER = ["R", "R'", "U", "U'", "F", "F'", "L", "L'", "D", "D'", "B", "B'"]

    def it(t):
        if t.endswith("'"):
            return t[:-1]
        if t.endswith("2"):
            return t
        return t + "'"

    out = []
    seen = set()
    for a in WIDE:
        ia = it(a)
        for L in range(1, max_outer_len + 1):
            for combo in itertools.product(OUTER, repeat=L):
                seq = ml._compress([a] + list(combo) + [ia] + [it(x) for x in reversed(combo)])
                k = tuple(seq)
                if k in seen:
                    continue
                seen.add(k)
                eff = me.compute_effect(seq)
                if not (eff.centers_ok and eff.fixed_centers_ok):
                    continue
                if eff.moves_whole_slots():
                    continue
                if eff.middle_cycles() or eff.left_wing_cycles():
                    continue
                cyc = eff.right_wing_cycles()
                if len(cyc) != 1 or len(cyc[0]) != 2:
                    continue
                out.append(ms.Macro(
                    "PAR:" + "".join(seq), seq,
                    ms._map_from_perm(eff.middle_perm),
                    ms._map_from_perm(eff.left_wing_perm),
                    ms._flip_src_of(eff.middle_flip, eff.middle_perm),
                    ms._flip_src_of(eff.left_flip, eff.left_wing_perm)))
    return out


# --------------------------------------------------------------------------
# 抽象求解
# --------------------------------------------------------------------------

def two_phase_solve(st, trans, mid_only, tmaps, mmaps, iters=200000):
    """transport 解 wing，再中棱宏解 mid。返回宏序列或 None。"""
    mid = st[:N]
    wing = st[N:]
    wseq = ms._solve_perm(wing, tmaps, iters)
    if wseq is None:
        return None
    cur_mid = mid
    used = []
    for mp in wseq:
        macro = next(mm for mm in trans if tuple(mm.mid_map) == mp)
        cur_mid = tuple(cur_mid[mp[i]] for i in range(N))
        used.append(macro)
    mseq = ms._solve_perm(cur_mid, mmaps, iters)
    if mseq is None:
        return None
    for mp in mseq:
        macro = next(mm for mm in mid_only if tuple(mm.mid_map) == mp)
        used.append(macro)
    return used


def solve_joint(st, trans, mid_only, tmaps, mmaps, lw_parity, iters=200000):
    """尝试解 abstract 到 identity。返回 (ok, macro_seq, note)。"""
    mid = st[:N]
    wing = st[N:]
    mid_p = perm_sign(mid)
    wing_p = perm_sign(wing)
    if mid_p == -1 and wing_p == -1 and mid_p != wing_p:
        # unreachable (equality of parity not satisfiable with even macros on mid)
        pass
    if mid_p == -1:
        # mid 奇：偶宏无法把 mid 归位
        if wing_p == -1 and mid_p == wing_p:
            # both odd: joint "even"? but mid odd still blocks
            pass
        return (False, None,
                f"mid parity odd ({mid_p}) -> need mid-parity macro (not found); "
                "only even macros touch mid")
    # mid 偶
    if wing_p == 1:
        plan = two_phase_solve(st, trans, mid_only, tmaps, mmaps, iters)
        if plan is not None:
            return True, plan, "two_phase (wing even)"
        return False, None, "wing even but not transport-reducible / mid residue unsolvable"
    # wing 奇, mid 偶
    for m in lw_parity:
        ns = ms.apply_macro_to_state(st, m.mid_map, m.wing_map)
        plan = two_phase_solve(ns, trans, mid_only, tmaps, mmaps, iters)
        if plan is not None:
            return True, [m] + plan, "lw-parity(1) + two_phase"
    return False, None, "wing odd; single lw-parity macro insufficient (needs joint search)"


# --------------------------------------------------------------------------
# 真实回放统计
# --------------------------------------------------------------------------

def replay_and_stat(cube_paired, macro_seq):
    """在已配翼的 cube 上回放宏序列，统计 VALID / 朝向 / 中心。"""
    from solver.edge5.state import center_color_off
    from solver.edge5.free_slice import _fixed_centers_preserved
    c = cube_paired.clone()
    move = 0
    for m in macro_seq:
        me.apply_macro(c, m.seq)
        move += len(m.seq)
    count_valid = ts.count_valid(c)
    center_off = center_color_off(c)
    fixed = _fixed_centers_preserved(c)
    defects = {n: ts.defect_kind(c, n) for n in ts.SLOT_NAMES}
    return dict(count_valid=count_valid, center_off=center_off, fixed=fixed,
                defects=defects, move_count=move)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

if __name__ == "__main__":
    trans, mid_only, tmaps, mmaps = build_transport_and_middle()
    lw_parity = collect_lw_odd_parity()
    rw_parity = collect_rw_odd_parity()
    print(f"transport={len(trans)} middle={len(mid_only)} "
          f"lw_parity(odd-2cyc)={len(lw_parity)} rw_parity={len(rw_parity)}")

    names = ["flip_seed19.json", "flip_seed2.json", "flip_seed51.json",
             "flip_seed23.json", "flip_seed4.json", "flip_seed7.json"]
    print("\n=== 配翼后 → 抽象归属求解 ===")
    for name in names:
        c = fixture(name)
        pm = p5.solve_wing_pairs(c)
        c2 = c.clone()
        c2.apply_moves(pm)
        st = ms.abstract_state(c2)
        mid = st[:N]
        wing = st[N:]
        ok, plan, note = solve_joint(st, trans, mid_only, tmaps, mmaps, lw_parity)
        header = (f"{name}: mid={'e' if perm_sign(mid)==1 else 'o'} "
                  f"wing={'e' if perm_sign(wing)==1 else 'o'} -> identity={ok} "
                  f"steps={len(plan) if plan else 0} [{note}]")
        print(header)
        if ok:
            stat = replay_and_stat(c2, plan)
            print(f"   replay: count_valid={stat['count_valid']} "
                  f"center_off={stat['center_off']} fixed={stat['fixed']} "
                  f"macro_steps={len(plan)} moves={stat['move_count']}")
            print(f"   defects: {stat['defects']}")
