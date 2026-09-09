"""中棱朝向修正：消除「中棱相对翼内部翻转」，使 tredge 内部一致。

背景（见 PROGRESS.md 第 11 节）：`reduce5` 只把中棱与翼的**色对**对齐
（`mid_home == wing_home`），不保证同槽三块在槽两面上同色同朝向。
`build_reduced_facelets` 只读中棱，故这种「中棱相对翼内部翻转」会被
虚拟 3x3 掩盖，回放后整体仍不复原。

本模块用「中棱恒等置换 + 翻转偶数个中棱」的宏词，把
`d = mid_orient XOR wing_orient` 线性消去：

- 只用 `wing_map == identity` 的中棱宏（翼完全不动），因此 `mid==wing`
  的色对对齐在修正过程中保持不变；
- 这类宏对朝向的作用对任意起始态都是**固定的 XOR 掩码**（朝向更新是仿射变换，
  恒等置换词只有平移项），故「使 `mo == wo`」等价于求掩码子集 XOR = d
  —— 纯 GF(2) 线性代数。

朝向模型（已实证，见 PROGRESS.md 11.3）：每个宏的翻转增量只依赖**源位置 q**，
`new_orient[dest] = orient[q] XOR delta[q]`。掩码库由 BFS（深度<=3）枚举得到。

仅用于研究 oracle；不依赖 solver/edge5 的搜索类。
"""
from __future__ import annotations

import heapq
import os
import pickle
from typing import Dict, List, Optional, Tuple

from cube.cube5 import Cube5
from cube.coordinates import FACE_AXIS_SIGN, FACE_NORMALS
from cube.cubie_model import is_fixed_face_center
from solver.edge5.positions import slot

from . import terminal_solver as ms
from . import terminal_state as ts
from .terminal_solver import me

_HERE = os.path.dirname(os.path.abspath(__file__))
SLOTS: List[str] = list(ms.SLOTS)
N = 12
_IDENTITY = tuple(range(N))
_CACHE_FILE = os.path.join(_HERE, "midflip_cache.pkl")


# --------------------------------------------------------------------------
# 朝向读取
# --------------------------------------------------------------------------

def face_colors(cube: Cube5) -> Dict[str, str]:
    """由 6 个固定面心得到 face -> 颜色。"""
    inv = {v: k for k, v in FACE_AXIS_SIGN.items()}
    out: Dict[str, str] = {}
    for cb in cube.cubies.values():
        if is_fixed_face_center(cb):
            ax = [i for i, v in enumerate(cb.pos) if v != 0][0]
            sg = 1 if cb.pos[ax] > 0 else -1
            f = inv.get((ax, sg))
            if f is not None:
                out[f] = list(cb.stickers.values())[0]
    return out


def orient_bits(cube: Cube5, fc: Optional[Dict[str, str]] = None) -> Tuple[List[int], List[int]]:
    """返回 (mid_orient[12], left_wing_orient[12])。

    `orient[i] = 0` 当该块在槽主面（槽名首字母）的颜色 == 其 home 主面色。
    """
    if fc is None:
        fc = face_colors(cube)
    mo = [0] * N
    wo = [0] * N
    for i, nm in enumerate(SLOTS):
        s = slot(nm)
        mcb = cube.cubies.get(s.middle)
        wcb = cube.cubies.get(s.left_wing)
        if mcb is not None:
            h = ts.logical_slot_of(frozenset(mcb.stickers.values()))
            mo[i] = 0 if mcb.stickers.get(FACE_NORMALS[nm[0]]) == fc[h[0]] else 1
        if wcb is not None:
            h = ts.logical_slot_of(frozenset(wcb.stickers.values()))
            wo[i] = 0 if wcb.stickers.get(FACE_NORMALS[nm[0]]) == fc[h[0]] else 1
    return mo, wo


def _mid_delta(macro) -> Tuple[int, ...]:
    """宏的 12 位中棱朝向增量（按源位置 q 索引）。"""
    c = Cube5.solved()
    me.apply_macro(c, macro.seq)
    fc = face_colors(c)
    delta = [0] * N
    for nm in SLOTS:
        mcb = c.cubies.get(slot(nm).middle)
        if mcb is None:
            continue
        q = ms.SLOT_INDEX[ts.logical_slot_of(frozenset(mcb.stickers.values()))]
        delta[q] = 0 if mcb.stickers.get(FACE_NORMALS[nm[0]]) == fc[SLOTS[q][0]] else 1
    return tuple(delta)


# --------------------------------------------------------------------------
# 掩码库：中棱恒等置换 + 翻转 2 个中棱的宏词
# --------------------------------------------------------------------------

def _step(perm, orient, mp, md):
    return (tuple(perm[mp[i]] for i in range(N)),
            tuple(orient[mp[i]] ^ md[mp[i]] for i in range(N)))


def build_patterns(max_depth: int = 3) -> Dict[int, Tuple[str, ...]]:
    """BFS 枚举「中棱恒等置换 + 朝向非零」的宏词，返回 {掩码: 展平动作元组}。"""
    macros = ms.build_all_macros()
    midonly = [M for M in macros if tuple(M.wing_map) == _IDENTITY]
    info = [(tuple(M.mid_map), _mid_delta(M), M) for M in midonly]
    start = (_IDENTITY, tuple([0] * N))
    seen = {start: ((), ())}
    front = [start]
    patterns: Dict[int, Tuple[str, ...]] = {}
    depth = 0
    while front and depth < max_depth:
        nf = []
        for st in front:
            for (mp, md, M) in info:
                ns = _step(st[0], st[1], mp, md)
                if ns in seen:
                    continue
                seen[ns] = (seen[st][0] + (M,), seen[st][1])
                if ns[0] == _IDENTITY and any(ns[1]):
                    flat = tuple(m for Mx in seen[ns][0] for m in Mx.seq)
                    patterns.setdefault(sum(b << i for i, b in enumerate(ns[1])), flat)
                nf.append(ns)
        front = nf
        depth += 1
    return patterns


_PATTERNS_CACHE: Optional[Dict[int, Tuple[str, ...]]] = None


def _load_patterns() -> Dict[int, Tuple[str, ...]]:
    global _PATTERNS_CACHE
    if _PATTERNS_CACHE is not None:
        return _PATTERNS_CACHE
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "rb") as f:
                data = pickle.load(f)
            if data.get("version") == 1 and data.get("patterns"):
                _PATTERNS_CACHE = data["patterns"]
                return _PATTERNS_CACHE
        except Exception:
            pass
    patterns = build_patterns()
    try:
        with open(_CACHE_FILE, "wb") as f:
            pickle.dump({"version": 1, "patterns": patterns}, f)
    except Exception:
        pass
    _PATTERNS_CACHE = patterns
    return patterns


_DIST_MAP: Optional[Dict[int, int]] = None
_INF = 1 << 30


def orient_distance_map() -> Dict[int, int]:
    """全掩码空间（<=4096）的最少步数距离表；用于候选终态评分。"""
    global _DIST_MAP
    if _DIST_MAP is None:
        items = list(_load_patterns().items())
        dist: Dict[int, int] = {0: 0}
        pq: List[Tuple[int, int]] = [(0, 0)]
        while pq:
            d, mask = heapq.heappop(pq)
            if dist.get(mask) != d:
                continue
            for bits, flat in items:
                nm = mask ^ bits
                nd = d + len(flat)
                if nd < dist.get(nm, _INF):
                    dist[nm] = nd
                    heapq.heappush(pq, (nd, nm))
        _DIST_MAP = dist
    return _DIST_MAP


def orient_cost(target: int) -> int:
    """掩码 `target` 的最少中棱朝向修正步数；不可达返回一个大整数。"""
    if target == 0:
        return 0
    return orient_distance_map().get(target, _INF)


def orient_mask(cube: Cube5) -> int:
    """当前 cube 的 `mid_orient XOR wing_orient` 12 位掩码。"""
    fc = face_colors(cube)
    mo, wo = orient_bits(cube, fc)
    return sum((mo[i] ^ wo[i]) << i for i in range(N))



_SOLVE_PREV_SRC: Optional[Dict[int, Tuple[str, ...]]] = None
_SOLVE_PREV: Dict[int, Tuple[int, Tuple[str, ...]]] = {}


def _build_solve_prev(patterns: Dict[int, Tuple[str, ...]]) -> Dict[int, Tuple[int, Tuple[str, ...]]]:
    """对全 12 位掩码空间做一次 Dijkstra，返回 {掩码: (前驱掩码, 宏词)}。"""
    items = list(patterns.items())
    dist: Dict[int, Tuple[int, int]] = {0: (0, 0)}
    prev: Dict[int, Tuple[int, Tuple[str, ...]]] = {}
    pq: List[Tuple[int, int, int]] = [(0, 0, 0)]  # (总步数, 词条数, 掩码)
    while pq:
        moves, words, mask = heapq.heappop(pq)
        if dist.get(mask) != (moves, words):
            continue
        for bits, flat in items:
            nm = mask ^ bits
            cand = (moves + len(flat), words + 1)
            if nm not in dist or cand < dist[nm]:
                dist[nm] = cand
                prev[nm] = (mask, flat)
                heapq.heappush(pq, (cand[0], cand[1], nm))
    return prev


def solve_mask(target: int, patterns: Dict[int, Tuple[str, ...]]) -> Optional[List[Tuple[str, ...]]]:
    """求掩码子集 XOR == target 的**最少总步数**解；返回对应宏词列表，无解返回 None。

    掩码空间仅 12 位（4096 状态）。对固定的 `patterns` 只做一次全空间 Dijkstra
    （以「总动作数」为主代价、宏词条数为次代价），之后任意 target 直接回溯，
    避免每次候选都重跑 Dijkstra。高斯消去只保证有解，这里额外保证步数最少。
    """
    if target == 0:
        return []
    global _SOLVE_PREV_SRC, _SOLVE_PREV
    if _SOLVE_PREV_SRC is not patterns:
        _SOLVE_PREV = _build_solve_prev(patterns)
        _SOLVE_PREV_SRC = patterns
    prev = _SOLVE_PREV
    if target not in prev:
        return None
    out: List[Tuple[str, ...]] = []
    cur = target
    while cur != 0:
        pm, flat = prev[cur]
        out.append(flat)
        cur = pm
    out.reverse()
    return out


# --------------------------------------------------------------------------
# 对外入口
# --------------------------------------------------------------------------

def fix_middle_orientation(cube: Cube5) -> Tuple[Optional[List[str]], Dict]:
    """让 `mid_orient == wing_orient`（中棱与翼内部一致），不改变色对归属。

    成功返回 (moves, info)，无解返回 (None, info)。不修改输入 cube。
    """
    info: Dict = {}
    fc = face_colors(cube)
    mo, wo = orient_bits(cube, fc)
    d = sum((mo[i] ^ wo[i]) << i for i in range(N))
    info["d_popcount"] = bin(d).count("1")
    if d == 0:
        info["fix_words"] = 0
        return [], info
    patterns = _load_patterns()
    words = solve_mask(d, patterns)
    if words is None:
        info["error"] = "no GF(2) solution for orientation mask"
        return None, info
    moves: List[str] = []
    for w in words:
        moves.extend(w)
    info["fix_words"] = len(words)
    return moves, info
