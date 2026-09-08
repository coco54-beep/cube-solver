"""已验证的纯净 3-cycle 宏库（Gate 5c / plan.md 宏 A）。

核心突破：`E R2 E' R2` 是**纯净中棱 3-cycle** 宏（中棱三循环、左右翼不动、
中心归面、6 固定面心不动）。基础交换子 `[slice, outer]` 得 24 个环内宏，
经纯外层共轭扩展覆盖全部 12 槽（232 种、完全对称、每可达组合双向可达）。

本模块提供：
- `BASE_MIDDLE_3CYCLES`：24 个基础中棱 3-cycle 宏（(宏串, 中棱循环)）。
- `conjugate_for_target(macro, cycle, target)`：用纯外层 setup 把宏共轭到目标槽组合。
- `build_reachable_3cycles()`：返回 {frozenset(三槽) : [(宏串, 中棱循环, 方向)]}。
  仅含可达的三槽组合（实测 116/220，全部双向）。

注意：纯净**左/右翼** 3-cycle 宏在基础交换子空间内**尚未找到**（缺口），
见 `MIDDLE_ANCHOR_UNREACHABLE.md` 之外的独立补充记录。

真实 5x5 replays 由 `macro_effect.compute_effect` 验证；本库只存已验证的宏。
"""
from __future__ import annotations

import itertools
import os
import sys
from typing import Dict, List, Set, Tuple

_REF_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_REF_DIR, "..", "..", "..", "..")))
sys.path.insert(0, _REF_DIR)

from macro_effect import compute_effect  # noqa: E402

SLICE = ["M", "M'", "M2", "E", "E'", "E2", "S", "S'", "S2"]
WIDE = ["2R", "2R'", "2L", "2L'", "2U", "2U'", "2D", "2D'", "2F", "2F'", "2B", "2B'"]
OUTER = ["R", "R'", "U", "U'", "F", "F'", "L", "L'", "D", "D'", "B", "B'"]

ALL_SLOTS = ["UF", "UR", "UB", "UL", "DF", "DR", "DB", "DL", "FR", "FL", "BR", "BL"]


def _inv(t: str) -> str:
    # 数字前缀 + 字母 + 尾缀
    i = 0
    while i < len(t) and t[i].isdigit():
        i += 1
    base = t[i:]  # 如 R, R', R2, M, M', M2
    if base.endswith("'"):
        return t[:i] + base[:-1]
    if base.endswith("2"):
        return t[:i] + base
    return t[:i] + base + "'"


def _split(t: str):
    """返回 (数字前缀 int, 字母 base str, count int)。"""
    i = 0
    while i < len(t) and t[i].isdigit():
        i += 1
    prefix = int(t[:i]) if i > 0 else 1  # 1=单层, 2=宽层; 切片 M/E/S 也归为 1 层但 base 是 M/E/S
    base_str = t[i:]
    if base_str.endswith("'"):
        letter = base_str[:-1]
        cnt = 3
    elif base_str.endswith("2"):
        letter = base_str[:-1]
        cnt = 2
    else:
        letter = base_str
        cnt = 1
    # 对宽层/面转，base 是字母；对切片 M/E/S 也是字母。
    return prefix, letter, cnt


def _compress(tokens) -> List[str]:
    stacked = []  # [(prefix, letter, count)]
    for t in tokens:
        prefix, letter, cnt = _split(t)
        while stacked and stacked[-1][0] == prefix and stacked[-1][1] == letter:
            prev = stacked[-1][2]
            cnt = (prev + cnt) % 4
            stacked.pop()
        if cnt != 0:
            stacked.append((prefix, letter, cnt))
    out = []
    for prefix, letter, cnt in stacked:
        suffix = {1: "", 2: "2", 3: "'"}[cnt]
        if prefix == 1:
            out.append(letter + suffix)
        else:
            out.append(str(prefix) + letter + suffix)
    return out


def _middle_cycle_of(seq) -> List[Tuple[str, ...]]:
    e = compute_effect(seq)
    return e.middle_cycles()


def _is_pure_middle(seq) -> bool:
    e = compute_effect(seq)
    if not (e.centers_ok and e.fixed_centers_ok):
        return False
    if e.moves_whole_slots():
        return False
    cyc = e.middle_cycles()
    if len(cyc) != 1 or len(cyc[0]) != 3:
        return False
    if e.left_wing_cycles() or e.right_wing_cycles():
        return False
    return True


def _build_base():
    """build 基础纯净中棱 3-cycle 宏。

    枚举 `[A, B] = A B A' B'`，其中 B 为外层 1~2 步（压缩后），
    A 为切片/宽层；用 `compute_effect` 实跑验证纯净中棱 3-cycle。
    """
    found = []
    seen = set()
    # 外层 1~2 步（含压缩得到 R2 等），去重
    basis = []
    bs = set()
    for b1 in OUTER:
        for b2 in OUTER:
            t = tuple(_compress([b1, b2]))
            if t not in bs and t:
                bs.add(t)
                basis.append(list(t))
    for a in SLICE + WIDE:
        for b in basis:
            seq = _compress([a] + b + [_inv(a)] + [_inv(x) for x in reversed(b)])
            if tuple(seq) in seen:
                continue
            # 避免太长的重复；先判断中心回归
            if not _is_pure_middle(seq):
                continue
            seqt = tuple(seq)
            seen.add(seqt)
            cyc = _middle_cycle_of(seq)[0]
            found.append((list(seq), tuple(cyc)))
    return found


BASE_MIDDLE_3CYCLES: List[Tuple[List[str], Tuple[str, ...]]] = _build_base()


def _outer_setups(max_len=2):
    out = []
    seen = {tuple()}
    frontier = [[]]
    for _ in range(max_len):
        nxt = []
        for seq in frontier:
            for mv in OUTER:
                ns = _compress(seq + [mv])
                if tuple(ns) in seen:
                    continue
                seen.add(tuple(ns))
                out.append(ns)
                nxt.append(ns)
        frontier = nxt
    return out


def build_reachable_3cycles():
    """返回 {frozenset(三槽) : [(压缩宏串, 中棱循环元组, is_reverse)]}。

    覆盖全部 12 槽、完全对称。仅含可达组合（实测 116/220，全双向）。
    """
    lib: Dict[frozenset, List[Tuple[List[str], Tuple[str, ...], bool]]] = {}
    for seq, cycle in BASE_MIDDLE_3CYCLES:
        key = frozenset(cycle)
        lib.setdefault(key, []).append((list(seq), tuple(cycle), False))
        # 反向
        rev_seq = _compress([_inv(t) for t in reversed(seq)])
        rev_cyc = _middle_cycle_of(rev_seq)[0]
        lib.setdefault(key, []).append((list(rev_seq), tuple(rev_cyc), True))
    for setup in _outer_setups():
        for seq, cycle in BASE_MIDDLE_3CYCLES:
            conj = _compress(setup + list(seq) + [_inv(t) for t in reversed(setup)])
            if not _is_pure_middle(conj):
                continue
            c = _middle_cycle_of(conj)[0]
            key = frozenset(c)
            lib.setdefault(key, []).append((list(conj), tuple(c), False))
            rev = _compress([_inv(t) for t in reversed(conj)])
            rc = _middle_cycle_of(rev)[0]
            lib.setdefault(frozenset(rc), []).append((list(rev), tuple(rc), True))
    return lib


REACHABLE = build_reachable_3cycles()


def monkey_setup_for(seq: List[str]) -> List[str]:
    return seq
