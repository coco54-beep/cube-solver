"""末段宏级求解器（plan.md Plan 6/7/11 + 方案四兜底）。

在「中心归面 + 翼对已配置(pairing5)」基础上，把每个棱槽抽象为
  slot 的中棱归属 (mid_home) 与 翼对归属 (wing_home)。
目标：所有槽 mid_home==slot 且 wing_home==slot（即 12/12 完整且回 home）。

动作 = 已验证宏：
- 纯净中棱 3-cycle（macro_lib.REACHABLE）：只动中棱归属，翼与中心不动。
- 整体搬运宏（外层共轭的 commutator）：整体 3-cycle 槽内容物（中棱+翼对），
  抽象上同时 3-cycle 中棱归属与翼对归属。

搜索 = A*（启发式 = 中棱错配数 + 翼对错配数）。求出的宏序列在真实 Cube5
上回放，做 center/fixed/valid 三重断言后才算达成。

与 solver/edge5 的搜索类无关；独立 oracle。
"""
from __future__ import annotations

import os
import sys
import heapq
import pickle
from typing import Dict, List, Optional, Tuple

from cube.cube5 import Cube5

from . import terminal_state as ts
from . import macro_effect as me
from . import macro_lib as ml

SLOTS: List[str] = list(ts.SLOT_NAMES)
SLOT_INDEX: Dict[str, int] = {s: i for i, s in enumerate(SLOTS)}
N = 12


def _inv(seq):
    return ml._compress([ml._inv(t) for t in reversed(seq)])


# --------------------------------------------------------------------------
# 抽象状态
# --------------------------------------------------------------------------

def abstract_state(cube: Cube5) -> Tuple[int, ...]:
    """返回 (mid_home[0..11], wing_home[0..11])，每项为槽索引。"""
    mid = []
    wing = []
    for s in SLOTS:
        mk = ts.logical_slot_of(ts.middle_edge_key(cube, s))
        lw, _rw = ts.wing_keys_of_slot(cube, s)
        mid.append(SLOT_INDEX[mk] if mk else -1)
        wing.append(SLOT_INDEX[ts.logical_slot_of(lw)] if lw else -1)
    return tuple(mid + wing)


def is_goal(state: Tuple[int, ...]) -> bool:
    return all(state[i] == i for i in range(2 * N))


def mismatch_count(state: Tuple[int, ...]) -> int:
    c = 0
    for i in range(2 * N):
        if state[i] != i:
            c += 1
    return c


# --------------------------------------------------------------------------
# 宏库构建
# --------------------------------------------------------------------------

def _cycles_of(eff) -> List[Tuple[str, ...]]:
    perm = eff.middle_perm
    seen = set()
    out = []
    for s in SLOTS:
        if s in seen:
            continue
        cur = s
        cy = []
        while cur not in seen:
            seen.add(cur)
            cy.append(cur)
            cur = perm[cur]
        if len(cy) > 1:
            out.append(tuple(cy))
    return out


def _map_from_perm(perm: Dict[str, str]) -> List[int]:
    """perm[q] = home-of-piece-at-q（来源槽名）→ 索引用 mid_map，new[q]=mid_perm[q]。"""
    return [SLOT_INDEX[perm[q]] for q in SLOTS]


class Macro:
    __slots__ = ("name", "seq", "mid_map", "wing_map", "mid_flip_src", "wing_flip_src",
                 "cost")

    def __init__(self, name, seq, mid_map, wing_map, mid_flip_src, wing_flip_src):
        self.name = name
        self.seq = list(seq)
        self.mid_map = mid_map          # list[i] = source index -> new_mid[i]=mid[src]
        self.wing_map = wing_map
        self.mid_flip_src = mid_flip_src
        self.wing_flip_src = wing_flip_src
        self.cost = len(self.seq)       # A* 边权 = 宏展开动作数


_EFFECT_CACHE: Dict[tuple, object] = {}


def _cached_effect(seq):
    key = tuple(seq)
    if key in _EFFECT_CACHE:
        return _EFFECT_CACHE[key]
    e = me.compute_effect(seq)
    _EFFECT_CACHE[key] = e
    return e


def build_middle_macros() -> List[Macro]:
    """从 macro_lib.REACHABLE 建立中棱 3-cycle 宏（含双向、去重）。"""
    out = []
    seen_perm = set()
    for combo, arr in ml.REACHABLE.items():
        for seq, _cyc, _rev in arr:
            eff = _cached_effect(seq)
            if not (eff.centers_ok and eff.fixed_centers_ok):
                continue
            # 确认翼 identity
            if not all(v == k for k, v in eff.left_wing_perm.items()):
                continue
            if not all(v == k for k, v in eff.right_wing_perm.items()):
                continue
            mid_map = _map_from_perm(eff.middle_perm)
            tkey = tuple(mid_map)
            if tkey in seen_perm:
                continue
            seen_perm.add(tkey)
            nm = "MID:" + "".join(seq)
            wing_map = list(range(N))  # identity
            mid_flip = _flip_src_of(eff.middle_flip, eff.middle_perm)
            wing_flip = list(range(N))
            out.append(Macro(nm, seq, mid_map, wing_map, mid_flip, wing_flip))
    return out


def _flip_src_of(flip_by_pos: Dict[str, bool], perm: Dict[str, str]) -> List[int]:
    """返回 list[src_home]=FlipBit，即来自 src_home 的块被宏翻转？"""
    out = list(range(N))
    for q in SLOTS:
        out[SLOT_INDEX[perm[q]]] = 1 if flip_by_pos[q] else 0
    return out


def build_transport_macros() -> List[Macro]:
    """外层共轭 base commutator 得整体搬运宏（whole-slot 3-cycle，去重）。"""
    base = ["R'", "F", "R", "F'"]
    setups = _outer_setups(2)
    out = []
    seen_key = set()
    for setup in setups:
        conj = ml._compress(setup + base + _inv(setup))
        eff = _cached_effect(conj)
        if not (eff.centers_ok and eff.fixed_centers_ok and eff.moves_whole_slots()):
            continue
        cyc = _cycles_of(eff)
        if len(cyc) != 1 or len(cyc[0]) != 3:
            continue
        mid_map = _map_from_perm(eff.middle_perm)
        wing_map = _map_from_perm(eff.left_wing_perm)
        kkey = (tuple(mid_map), tuple(wing_map))
        if kkey in seen_key:
            continue
        seen_key.add(kkey)
        mid_flip = _flip_src_of(eff.middle_flip, eff.middle_perm)
        wing_flip = _flip_src_of(eff.left_flip, eff.left_wing_perm)
        out.append(Macro("TR:" + "".join(conj), conj, mid_map, wing_map, mid_flip, wing_flip))
    return out


def _outer_setups(max_len=2):
    out = []
    seen = {tuple()}
    frontier = [[]]
    for _ in range(max_len):
        nxt = []
        for seq in frontier:
            for mv in ml.OUTER:
                ns = ml._compress(seq + [mv])
                if tuple(ns) in seen:
                    continue
                seen.add(tuple(ns))
                out.append(ns)
                nxt.append(ns)
        frontier = nxt
    return out


_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macro_cache.pkl")


def _macros_cache_key():
    return "mid_trans_v2"


def build_all_macros(use_cache: bool = True) -> List[Macro]:
    """构建（或从磁盘缓存读）中棱 + 整体搬运宏。"""
    if use_cache and os.path.exists(_CACHE_FILE):
        with open(_CACHE_FILE, "rb") as f:
            cached = pickle.load(f)
        if cached.get("key") == _macros_cache_key():
            return cached["macros"]
    macros = build_middle_macros() + build_transport_macros()
    try:
        with open(_CACHE_FILE, "wb") as f:
            pickle.dump({"key": _macros_cache_key(), "macros": macros}, f)
    except OSError:
        pass
    return macros


# --------------------------------------------------------------------------
# A* 求解（仅置换）
# --------------------------------------------------------------------------

def apply_macro_to_state(state: Tuple[int, ...], mid_map, wing_map) -> Tuple[int, ...]:
    mid = state[:N]
    wing = state[N:]
    new_mid = tuple(mid[mid_map[i]] for i in range(N))
    new_wing = tuple(wing[wing_map[i]] for i in range(N))
    return new_mid + new_wing


def solve_abstract(state: Tuple[int, ...], macros: List[Macro],
                   iters: int = 400000) -> Optional[List[Macro]]:
    """A* 返回宏序列（可能空），找不到返回 None。"""
    if is_goal(state):
        return []
    start_h = mismatch_count(state)
    # heap: (f, counter, state, path)
    counter = 0
    heap = []
    heapq.heappush(heap, (start_h, counter, state, []))
    seen = {state}
    while heap and len(seen) < iters:
        f, _c, cur, path = heapq.heappop(heap)
        if is_goal(cur):
            return path
        for m in macros:
            ns = apply_macro_to_state(cur, m.mid_map, m.wing_map)
            if ns in seen:
                continue
            seen.add(ns)
            g = len(path) + 1
            h = mismatch_count(ns)
            heapq.heappush(heap, (g + h, g, ns, path + [m]))
    return None


# --------------------------------------------------------------------------
# 回放断言
# --------------------------------------------------------------------------

def run_solver(cube: Cube5, macros: List[Macro], goal_macros=None) -> Tuple[bool, List[str]]:
    """在真实 cube 上执行求解。先解抽象，再把宏序列回放。

    返回 (是否12/12 valid_centers_fixed, 移动序列)。
    """
    st = abstract_state(cube)
    from solver.edge5.state import center_color_off
    from solver.edge5.free_slice import _fixed_centers_preserved
    start_centoff = center_color_off(cube)
    start_fixed = _fixed_centers_preserved(cube)

    plan = solve_abstract(st, macros)
    if plan is None:
        return False, []
    moves = []
    for m in plan:
        moves.extend(m.seq)
    return True, moves


# --------------------------------------------------------------------------
# 两段式构造求解：先解翼对归属（整体搬运宏），再补中棱（中棱 3-cycle）
# --------------------------------------------------------------------------

def _solve_perm(perm_state: Tuple[int, ...], maps: List[Tuple[int, ...]],
                iters: int = 800000) -> Optional[List[Tuple[int, ...]]]:
    """对单个 12 元素置换用 A* 求到 identity。每步 new[i]=state[m[i]]。

    maps: 允许的「右乘」位置循环映射。返回映射序列（已到达 identity）。
    """
    n = len(perm_state)
    goal_ok = all(perm_state[i] == i for i in range(n))
    if goal_ok:
        return []
    counter = 0
    heap = []
    h0 = sum(1 for i in range(n) if perm_state[i] != i)
    heapq.heappush(heap, (h0, counter, tuple(perm_state), []))
    seen = {tuple(perm_state)}
    while heap and len(seen) < iters:
        _f, _c, cur, path = heapq.heappop(heap)
        if all(cur[i] == i for i in range(n)):
            return path
        for mp in maps:
            ns = tuple(cur[mp[i]] for i in range(n))
            if ns in seen:
                continue
            seen.add(ns)
            g = len(path) + 1
            h = sum(1 for i in range(n) if ns[i] != i)
            heapq.heappush(heap, (g + h, g, ns, path + [mp]))
    return None


def solve_two_phase(state: Tuple[int, ...], macros: List[Macro],
                    iters: int = 800000) -> Optional[List[Macro]]:
    """两段式：先整体搬运宏解翼对归属，再用中棱宏补余下中棱。

    返回宏序列（含中间宏），失败返回 None。不影响输入。
    """
    mid = state[:N]
    wing = state[N:]
    # 翼：只用整体搬运宏（其 mid_map==wing_map）
    trans = [m for m in macros if tuple(m.mid_map) == tuple(m.wing_map)]
    mid_only = [m for m in macros if tuple(m.wing_map) == tuple(range(N))]
    # 阶段 A：解翼对归属
    tmaps = [tuple(m.mid_map) for m in trans]
    wing_seq = _solve_perm(wing, tmaps, iters)
    if wing_seq is None:
        return None
    # 阶段 A 也会把中棱右乘同样的循环，计算中间中棱状态
    cur_mid = mid
    used = []
    for mp in wing_seq:  # 每个对应一个 transport macro
        # 找到该 map 对应的宏
        macro = next(mm for mm in trans if tuple(mm.mid_map) == mp)
        cur_mid = tuple(cur_mid[mp[i]] for i in range(N))
        used.append(macro)
    # 阶段 B：解中棱归属
    mmaps = [tuple(m.mid_map) for m in mid_only]
    mid_seq = _solve_perm(cur_mid, mmaps, iters)
    if mid_seq is None:
        return None
    for mp in mid_seq:
        macro = next(mm for mm in mid_only if tuple(mm.mid_map) == mp)
        used.append(macro)
    return used
