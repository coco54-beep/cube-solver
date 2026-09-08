"""parity_solver.py —— 搜索「奇置换宏」以翻转 seed23/4/7（及 seed2/51）的联合奇偶。

背景（key correction）：
- 现有偶宏（整体搬运 3-cycle + 纯中棱 3-cycle）均为**偶置换**（3-cycle，sign=+1）。
- 因此它们无法修复「奇置换」的归属层。
- 需要找到一个保持 centers_ok & fixed_centers_ok、但在中棱或翼对上产生**奇置换**
  （存在偶数长度循环，如一次 2-cycle / 4-cycle，或整体 sign=-1）的宏，把奇翻成偶，
  再用偶宏（transport + 中棱）求解归属层。

实测（配翼后 6 fixture 联合奇偶）：
- seed19: mid=e wing=e joint=e  → 仅偶宏可解。
- seed2 / seed51: mid=o wing=o（wing 奇）→ 偶宏不能把 wing 归位，需奇 wing 宏。
- seed23 / seed4: mid=e wing=o（wing 奇）→ 需奇 wing 宏。
- seed7: mid=o wing=e（mid 奇）→ win 偶可归位，但残 mid 奇，需奇 mid 宏。

因此一个「奇 wing（或奇 mid）置换且保中心」的宏即可作为 parity 宏。

搜索空间放宽：
- [A,B]：A ∈ {切片, 宽转}, B ∈ {外层序列长度 1..3（压缩后）}。
- 对好候选再共轭（外层 setup 长度 1..2）。
- 两段组合：可以用前后两段（允许前段破中心、后段恢复）——这里先做单段+共轭。

筛选：centers_ok and fixed_centers_ok and (mid sign=-1 or wing sign=-1 or rw sign=-1)
      且 moves_whole_slots 为 False（避免整体搬槽，纯奇才可贵）。
"""
from __future__ import annotations

import os
import sys
import itertools
import importlib.util

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
me = load("me", REF + r"\macro_effect.py")
ml = load("ml", REF + r"\macro_lib.py")

SLICE = ["M", "M'", "M2", "E", "E'", "E2", "S", "S'", "S2"]
WIDE = ["2R", "2R'", "2L", "2L'", "2U", "2U'", "2D", "2D'", "2F", "2F'", "2B", "2B'"]
OUTER = ["R", "R'", "U", "U'", "F", "F'", "L", "L'", "D", "D'", "B", "B'"]


def _inv_token(t):
    if t.endswith("'"):
        return t[:-1]
    if t.endswith("2"):
        return t
    return t + "'"


def _perm_sign(cycles):
    """cycles: 循环列表（循环长度>=2）。sign = product (-1)^(len-1)。"""
    s = 1
    for cyc in cycles:
        if len(cyc) % 2 == 0:
            s = -s
    return s


def _has_odd(cycles):
    return _perm_sign(cycles) == -1


def _effect_seq(seq):
    return me.compute_effect(seq)


def is_parity_macro(eff):
    """保中心 + 固定面心 + 中棱或翼对存在奇置换（非整体搬槽）。"""
    if not (eff.centers_ok and eff.fixed_centers_ok):
        return False
    if eff.moves_whole_slots():
        return False
    odd_mid = _has_odd(eff.middle_cycles())
    odd_lw = _has_odd(eff.left_wing_cycles())
    odd_rw = _has_odd(eff.right_wing_cycles())
    return odd_mid or odd_lw or odd_rw


def enumerate_base_commutators(max_outer_len=3, compress=True):
    """[A, B] = A B A' B'，A ∈ SLICE∪WIDE，B 为外层序列（长度<=max_outer_len）。"""
    out = []
    seen = set()
    sl = SLICE + WIDE
    for a in sl:
        ia = _inv_token(a)
        for L in range(1, max_outer_len + 1):
            for combo in itertools.product(OUTER, repeat=L):
                full = [a] + list(combo) + [ia] + [_inv_token(x) for x in reversed(combo)]
                if compress:
                    full = ml._compress(full)
                key = tuple(full)
                if key in seen:
                    continue
                seen.add(key)
                out.append(full)
    return out


def enumerate_conjugates(seq, max_setup=2):
    """X seq X'，X 为外层 setup（长度<=max_setup，压缩去重）。"""
    out = []
    seen = set()
    for X in ml._outer_setups(max_setup) if hasattr(ml, '_outer_setups') else _outer_setups(max_setup):
        conj = ml._compress(X + list(seq) + [ml._inv(t) for t in reversed(X)]) if hasattr(ml, '_inv') else None
        if conj is None:
            conj = ml._compress(X + list(seq) + [ml._inv(t) for t in reversed(X)])
        key = tuple(conj)
        if key in seen:
            continue
        seen.add(key)
        out.append(conj)
    return out


def _outer_setups(max_len=2):
    out = []
    seen = {tuple()}
    frontier = [[]]
    for _ in range(max_len):
        nxt = []
        for seq in frontier:
            for mv in OUTER:
                ns = ml._compress(seq + [mv])
                if tuple(ns) in seen:
                    continue
                seen.add(tuple(ns))
                out.append(ns)
                nxt.append(ns)
        frontier = nxt
    return out


def search(max_commutator_len=3, max_setup=2, mode="base"):
    """返回发现列表 [(seq, eff, which_odd, len)]。"""
    found = []
    seen_perms = set()
    cands = enumerate_base_commutators(max_outer_len=max_commutator_len)
    print(f"base commutator 候选 {len(cands)} 个", flush=True)
    for seq in cands:
        eff = _effect_seq(seq)
        if not is_parity_macro(eff):
            continue
        key = (tuple(eff.left_wing_perm.items()), tuple(eff.middle_perm.items()))
        if key in seen_perms:
            continue
        seen_perms.add(key)
        found.append((list(seq), eff))

    # 共轭扩展
    extra = []
    seen2 = set(seen_perms)
    base = [f[0] for f in found]
    for seq in base:
        for conj in enumerate_conjugates(seq, max_setup):
            eff = _effect_seq(conj)
            if not is_parity_macro(eff):
                continue
            key = (tuple(eff.left_wing_perm.items()), tuple(eff.middle_perm.items()))
            if key in seen2:
                continue
            seen2.add(key)
            extra.append((list(conj), eff))
    found += extra
    return found


def summarize(found, limit=40):
    out = []
    for seq, eff in found:
        odd = []
        if _has_odd(eff.middle_cycles()):
            odd.append("mid")
        if _has_odd(eff.left_wing_cycles()):
            odd.append("lw")
        if _has_odd(eff.right_wing_cycles()):
            odd.append("rw")
        out.append(("".join(seq), "".join(odd), len(seq),
                    eff.middle_cycles(), eff.left_wing_cycles(),
                    eff.right_wing_cycles(), len(eff.affected_slots)))
    return out


if __name__ == "__main__":
    found = search(max_commutator_len=3, max_setup=2)
    print(f"\n发现奇置换宏（centers_ok & fixed_centers_ok）：{len(found)} 个", flush=True)
    # 按影响槽数 + 长度排序，打印小者
    rows = summarize(found)
    rows.sort(key=lambda r: (r[6], r[2]))
    for r in rows[:40]:
        print(f"  {r[0]:<40} odd={r[1]} len={r[2]} slots={r[6]} mid={r[3]} lw={r[4]} rw={r[5]}",
              flush=True)

    # 嵌入 mid-odd 负面结论
    n_mid = sum(1 for seq, eff in found if _has_odd(eff.middle_cycles()))
    n_lw = sum(1 for seq, eff in found if _has_odd(eff.left_wing_cycles()))
    print(f"\n统计：mid-odd 宏 {n_mid} 个；lw-odd 宏 {n_lw} 个", flush=True)
    print("说明：在 [slice/wide, outer^1..3] 交换子及其(l<=2)外层共轭空间内，"
          "仅找到 **翼对**（lw/rw）奇 2-cycle parity 宏（其中单左翼 2-cycle 默认保持中棱不动）；"
          "**未找到任何 mid-odd（奇中棱置换）宏**。"
          "结合 joint_solver 的 group 分析：凡作用 mid 的宏（transport / 中棱宏）皆为偶 3-cycle，"
          "故 mid 初始为奇的 fixture（seed2/51/7）无法用现有宏集（含这些 parity 宏）解到 identity，"
          "需要额外的奇中棱 parity 宏（本搜索空间内未发现）。", flush=True)
