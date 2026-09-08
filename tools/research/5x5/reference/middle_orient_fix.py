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

import os
import pickle
import sys
from typing import Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import terminal_solver as ms  # noqa: E402
import terminal_state as ts  # noqa: E402
from terminal_solver import me  # noqa: E402

from cube.cube5 import Cube5  # noqa: E402
from cube.coordinates import FACE_AXIS_SIGN, FACE_NORMALS  # noqa: E402
from cube.cubie_model import is_fixed_face_center  # noqa: E402
from solver.edge5.positions import slot  # noqa: E402

SLOTS: List[str] = list(ms.SLOTS)
N = 12
_IDENTITY = tuple(range(N))
_CACHE_FILE = os.path.join(_HERE, ".midflip_cache.pkl")


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


def _load_patterns() -> Dict[int, Tuple[str, ...]]:
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "rb") as f:
                data = pickle.load(f)
            if data.get("version") == 1 and data.get("patterns"):
                return data["patterns"]
        except Exception:
            pass
    patterns = build_patterns()
    try:
        with open(_CACHE_FILE, "wb") as f:
            pickle.dump({"version": 1, "patterns": patterns}, f)
    except Exception:
        pass
    return patterns


def _gf2_basis(patterns: Dict[int, Tuple[str, ...]]):
    piv: Dict[int, Tuple[int, List[Tuple[str, ...]]]] = {}
    for bits, mv in patterns.items():
        b = bits
        comb = [mv]
        while b:
            p = b.bit_length() - 1
            if p in piv:
                pb, pcomb = piv[p]
                b ^= pb
                comb = comb + pcomb
            else:
                piv[p] = (b, comb)
                break
    return piv


def solve_mask(target: int, patterns: Dict[int, Tuple[str, ...]]) -> Optional[List[Tuple[str, ...]]]:
    """求掩码子集 XOR == target；返回对应宏词列表，无解返回 None。"""
    piv = _gf2_basis(patterns)
    b = target
    comb: List[Tuple[str, ...]] = []
    while b:
        p = b.bit_length() - 1
        if p not in piv:
            return None
        pb, pcomb = piv[p]
        b ^= pb
        comb = comb + pcomb
    return comb


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
