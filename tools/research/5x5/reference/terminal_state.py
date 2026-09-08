"""末段 tredge 抽象状态与宏级求解（plan.md Plan 1 / 6 / 7）。

在「中心归面 + 翼对已用 pairing5 配齐」的基础上，把每个棱槽抽象为
`TredgeSlot`（中棱/左翼/右翼属于哪条逻辑棱 + 朝向），定义缺陷签名
（VALID / FLIPPED / MIDDLE_MISMATCH / LEFT_WING_MISMATCH / RIGHT_WING_MISMATCH /
MULTI_MISMATCH），并用已验证的「纯净中棱 3-cycle 宏」（宏库 macro_lib）在中棱
归属层做小型 BFS 求解（Plan 6/7 抽象规划器）。

与 `solver/edge5` 的搜索类无关；独立 oracle。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from cube.cube5 import Cube5

# --- 加载同目录模块（tredge / macro_lib / macro_effect）---
import os as _os
import sys as _sys

_REF = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _REF)
_sys.path.insert(0, _os.path.abspath(_os.path.join(_REF, "..", "..", "..", "..")))
for _m in ("tredge", "macro_lib", "macro_effect"):
    if _m not in _sys.modules:
        import importlib.util as _iu
        _spec = _iu.spec_from_file_location(_m, _os.path.join(_REF, _m + ".py"))
        _mod = _iu.module_from_spec(_spec)
        _sys.modules[_m] = _mod
        _spec.loader.exec_module(_mod)

from tredge import (  # noqa: E402
    SLOT_NAMES,
    middle_edge_key,
    wing_keys_of_slot,
    is_complete_tredge,
    tredge_oriented,
    face_colors,
)
from macro_lib import REACHABLE, BASE_MIDDLE_3CYCLES, _compress, _inv, ALL_SLOTS  # noqa: E402

# 逻辑棱色对 -> 目标槽（在 solved 态标定）。
_LOGGICAL_KEY: Dict[frozenset, str] = {}


def _calibrate():
    c = Cube5.solved()
    for n in SLOT_NAMES:
        _LOGGICAL_KEY[middle_edge_key(c, n)] = n


_calibrate()

# 中棱色对 -> 逻辑棱槽名
MIDDLE_KEY_TO_SLOT = dict(_LOGGICAL_KEY)


def logical_slot_of(key: frozenset) -> Optional[str]:
    return _LOGGICAL_KEY.get(key)


# --- plan.md Plan 1 抽象状态 ---


def _slot_defects(state: Cube5, name: str) -> Tuple[str, ...]:
    """该槽一个或多个缺陷类型（可能空=VALID）。"""
    mk = middle_edge_key(state, name)
    lw, rw = wing_keys_of_slot(state, name)
    if mk is None or lw is None or rw is None:
        return ("INCOMPLETE",)
    target = logical_slot_of(mk)
    lw_target = logical_slot_of(lw)
    rw_target = logical_slot_of(rw)
    if target is None or lw_target is None or rw_target is None:
        return ("UNKNOWN",)
    return (
        "MIDDLE_MISMATCH" if target != name else None,
        "LEFT_WING_MISMATCH" if lw_target != name else None,
        "RIGHT_WING_MISMATCH" if rw_target != name else None,
    )


def defect_kind(state: Cube5, name: str) -> str:
    """返回单标签缺陷类型（与 plan.md 命名一致），VALID 表示无缺陷。"""
    if is_complete_tredge(state, name):
        return "FLIPPED" if not tredge_oriented(state, name) else "VALID"
    ds = [d for d in _slot_defects(state, name) if d]
    if not ds:
        return "UNKNOWN"
    if all(d == "MIDDLE_MISMATCH" for d in ds) and len(ds) == 1:
        return "MIDDLE_MISMATCH"
    if all(d == "LEFT_WING_MISMATCH" for d in ds) and len(ds) == 1:
        return "LEFT_WING_MISMATCH"
    if all(d == "RIGHT_WING_MISMATCH" for d in ds) and len(ds) == 1:
        return "RIGHT_WING_MISMATCH"
    return "MULTI_MISMATCH"


def count_valid(state: Cube5) -> int:
    return sum(1 for n in SLOT_NAMES if is_complete_tredge(state, n) and tredge_oriented(state, n))


def tredge_summary(state: Cube5) -> Dict[str, str]:
    return {n: defect_kind(state, n) for n in SLOT_NAMES}


# --- 中棱 3-cycle 宏在「中棱归属」层的作用 ---
# 每个宏已知其产生的中棱 3-cycle（在 REACHABLE 中按槽组合索引）。
# 对任意状态，宏作为一个「置换」作用于中棱归属。为在抽象层应用，我们需要
# 宏对中棱的置换（循环）在「槽位置」上的作用：一个中棱 3-cycle 宏把
# 槽 A 的中棱移到 B，B 移到 C，C 移到 A（按宏的循环方向）。


def middle_perm_of_macro(cycle: Tuple[str, str, str]) -> Dict[str, str]:
    """把槽位置循环 (A B C) 转为中棱归属置换 dict {A:B, B:C, C:A}。
    即：槽 A 现在接受来自槽 A' 的中棱（应用后 A 的中棱 = 原槽 A 的位置在循环内的来源）。
    注意 sign: 应用 macro 到状态，使「进入槽 A 的中棱」来自循环中 A 的前一个槽。
    """
    return {cycle[i]: cycle[(i + 1) % 3] for i in range(3)}


def macro_search_for_middle(
    state: Cube5,
    protected: set,
    active: List[str],
    max_iters: int = 60,
):
    """在中棱归属层用 3-cycle 宏 BFS 求解。

    active: 允许动用的槽（末段 4 条）。目标：active 内所有槽的中棱归属 == 槽位
    且 active 之外的 protected 槽保持完整。返回 (动作序列, 是否成功)。

    说明：宏只做中棱 3-cycle（不动翼、中心归面），因此翼对与中心在本阶段不变。
    """
    from collections import deque

    # 宏集合：仅限那些「受影响三槽都在 active 内」的宏，避免破坏 protected。
    macros = []  # (中棱置换 dict, 原始槽组合 frozenset, 宏串)
    seen_m = set()
    for combo, arr in REACHABLE.items():
        if not combo.issubset(set(active)):
            continue
        # 每个组合取一个代表性宏（正方向）
        seq, cyc, _rev = arr[0]
        key = tuple(seq)
        if key in seen_m:
            continue
        seen_m.add(key)
        macros.append((middle_perm_of_macro(tuple(cyc)), combo, list(seq)))

    start = {n: (logical_slot_of(middle_edge_key(state, n)) or n) for n in active}
    if all(start[n] == n for n in active):
        return [], True

    # BFS over 中棱归属 tuples
    target = tuple(sorted(active))
    root = tuple(sorted((start[n] for n in active)))
    dist = {root: None}
    parent = {root: None}
    q = deque([root])
    found = None
    while q and found is None:
        cur = q.popleft()
        if cur == target:
            found = cur
            break
        for mp, combo, seq in macros:
            nxt = list(cur)
            # mp: {A:B, B:C, C:A} 槽位置置换。应用宏后，槽 X 的中棱 = 原来来源槽
            # 的中棱。mp 定义 X <- 来源 = 使进入 X 的中棱来自 mp 中映射到 X 的前身。
            # 用 mp 表示「槽 A 的中棱移到 B」：需从 cur（按槽排序）重排。
            d = dict(combo)  # placeholder
            # 计算新归属：位置为各 active 槽。应用置换后槽 B 取得槽 A 的中棱（A->B）。
            # 用映射 mid_from = {B:A, C:B, A:C}（A->B 表示 B 得到 A 的中棱）。
            mid_from = {mp[a]: a for a in mp}
            # 需要 cur 的槽序索引
            idx = {s: i for i, s in enumerate(sorted(active))}
            newvals = list(cur)
            for dst in mid_from:
                src = mid_from[dst]
                # dst 槽获得 src 槽的原中棱
                newvals[idx[dst]] = cur[idx[src]]
            nxt = tuple(newvals)
            if nxt in dist:
                continue
            dist[nxt] = (cur, seq)
            parent[nxt] = cur
            q.append(nxt)
        # 限制
        if len(dist) > 200000:
            break
    if found is None:
        return None, False
    # 重建路径
    path = []
    cur = found
    while dist[cur] is not None:
        prev, seq = dist[cur]
        path.append(seq)
        cur = prev
    path.reverse()
    moves = []
    for seq in path:
        moves.extend(seq)
    return moves, True
