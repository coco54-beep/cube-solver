"""5x5 中心同色等价求解（第二轮优化）。

精确求解（``solve_centers5``）要求每个活动中心块回到唯一 home 槽，因此会在
「面内同色块的置换」上浪费动作。本模块只要求中心「按颜色归面」——同一颜色的
中心块可互换——从而把长置换拆成更短的循环，显著减少 3-cycle 宏数量。

算法（corner / edge 两个轨道各自独立）：

1. 读状态：每个错色位置记录 ``(demand=所在面颜色, supply=块自身颜色)``。
2. 在 6 色有向多重图上把错色位置分解为闭合 trail（优先 3-cycle、再 2-cycle）。
   ``m[(demand, supply)]`` 计数；三角 ``A->B->C->A`` 即一个可一次归色的 3-cycle。
3. 每个 trail 对应一个位置循环：沿 trail 取具体位置，令块 ``p_i -> p_{i+1}``，
   由 ``supply(p_i) == demand(p_{i+1})`` 保证落位即归色。
4. 组装 net movement 置换 ``g``；奇偶只取决于循环个数（``parity=(W-T) mod 2``），
   优先筛偶置换分解，必要时在共享颜色顶点拼接两条 trail 翻转奇偶。
5. ``decompose_even_pos_to_home(g)`` 得正向 3-cycle 序列，逐个
   ``instantiate_center_3cycle`` 实例化为宏并施加（宏在另一轨道/固定面心上净不动）。
6. 从原状态重放校验中心已按颜色归面。

对随机分解做多次重启，取宏数量最少的方案。
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

from cube.cube5 import Cube5
from cube.coordinates import FACE_AXIS_SIGN, get_d_maxc

from .legal_moves import assert_legal_5x5_solution_moves
from .orbits import CenterOrbitKind, kind_of_position
from .permutation import (
    build_pos_to_home_permutation,
    decompose_even_pos_to_home,
    orbit_global_ids,
    permutation_parity,
)
from .primitives import (
    CENTER_INDEX,
    CENTER_ORDER,
    CORNER_BACKUP,
    CORNER_MAIN,
    EDGE_BACKUP,
    EDGE_COMM4,
    EDGE_MAIN,
    CenterPrimitive,
)
from .setup_cache import get_setup_table, instantiate_center_3cycle
from .solver import CenterSolveResult

# 失败错误码（与 solver.py 保持一致的命名风格）。
CENTER_REPLAY_MISMATCH = "CENTER_REPLAY_MISMATCH"
CENTER_COLOR_SOLVE_FAILED = "CENTER_COLOR_SOLVE_FAILED"

# 先解 edge（用 4 步联合换位子 EDGE_COMM4，会扰动 corner），再解 corner
# （用 edge-pure 基元，不扰动已解 edge）。
_ACTIVE_ORBITS: Tuple[CenterOrbitKind, ...] = (
    CenterOrbitKind.EDGE,
    CenterOrbitKind.CORNER,
)


# ---------------------------------------------------------------------------
# 颜色/位置辅助
# ---------------------------------------------------------------------------

def _face_of_position(pos: Tuple[int, int, int]) -> Optional[str]:
    _, maxc = get_d_maxc(5)
    for face, (axis, sign) in FACE_AXIS_SIGN.items():
        if pos[axis] == sign * maxc:
            return face
    return None


def _face_colors(cube: Cube5) -> Dict[str, str]:
    """从 6 个固定面心读取每个面的颜色。"""
    out: Dict[str, str] = {}
    for cubie in cube.cubies.values():
        if len(cubie.stickers) == 1 and sorted(abs(v) for v in cubie.home) == [0, 0, 6]:
            face = _face_of_position(cubie.home)
            if face is not None:
                out[face] = next(iter(cubie.stickers.values()))
    return out


def _single_color(cubie) -> str:
    return next(iter(cubie.stickers.values()))


def _wrong_positions(
    cube: Cube5,
    orbit: CenterOrbitKind,
    face_color: Dict[str, str],
) -> List[Tuple[Tuple[int, int, int], str, str]]:
    """返回该轨道所有错色位置的 (pos, demand, supply)。"""
    out: List[Tuple[Tuple[int, int, int], str, str]] = []
    for cubie in cube.cubies.values():
        if len(cubie.stickers) != 1:
            continue
        if kind_of_position(cubie.home) != orbit:
            continue
        supply = _single_color(cubie)
        demand = face_color.get(_face_of_position(cubie.pos))
        if demand is None:
            raise ValueError("中心位置不在任何外层面: %s" % (cubie.pos,))
        if supply != demand:
            out.append((cubie.pos, demand, supply))
    return out


def _positions_by_edge(
    wrong: Sequence[Tuple[Tuple[int, int, int], str, str]],
) -> Dict[Tuple[str, str], List[Tuple[int, int, int]]]:
    out: Dict[Tuple[str, str], List[Tuple[int, int, int]]] = defaultdict(list)
    for pos, demand, supply in wrong:
        out[(demand, supply)].append(pos)
    return out


# ---------------------------------------------------------------------------
# 颜色多重图分解（多次重启取宏数量最少）
# ---------------------------------------------------------------------------

def _decompose_trails(
    edges: Counter,
    colors: Sequence[str],
    rng: random.Random,
) -> List[List[Tuple[str, str]]]:
    """把 (demand, supply) 多重边集分解为若干闭合 trail。"""
    pool = Counter(edges)
    trails: List[List[Tuple[str, str]]] = []

    # 1) 贪心提取三角（3-cycle），一次归色 3 个位置。
    while True:
        cands = []
        for a in colors:
            for b in colors:
                for c in colors:
                    if pool[(a, b)] > 0 and pool[(b, c)] > 0 and pool[(c, a)] > 0:
                        cands.append(((a, b), (b, c), (c, a)))
        if not cands:
            break
        tr = rng.choice(cands)
        for e in tr:
            pool[e] -= 1
        trails.append(list(tr))

    # 2) 提取 2-cycle。
    for a in colors:
        for b in colors:
            if a < b:
                k = min(pool[(a, b)], pool[(b, a)])
                for _ in range(k):
                    pool[(a, b)] -= 1
                    pool[(b, a)] -= 1
                    trails.append([(a, b), (b, a)])

    # 3) 剩余边：沿 supply->demand 闭合 trail（图平衡，必然闭合）。
    remaining = [e for e, c in pool.items() for _ in range(c)]
    rng.shuffle(remaining)
    while remaining:
        start = remaining.pop()
        trail = [start]
        cur = start
        while True:
            idx = None
            for i, e in enumerate(remaining):
                if e[0] == cur[1]:
                    idx = i
                    break
            if idx is None:
                break
            nxt = remaining.pop(idx)
            trail.append(nxt)
            cur = nxt
        trails.append(trail)

    return trails


def _trail_cost(trails: Sequence[Sequence]) -> int:
    """3-cycle 宏数量上界估计：长度为 L 的循环需 floor(L/2) 个宏。"""
    return sum(len(t) // 2 for t in trails)


def _splice_to_even(
    trails: List[List[Tuple[str, str]]],
) -> Optional[List[List[Tuple[str, str]]]]:
    """把两条共享颜色的闭合 trail 在公共顶点处拼接为一条（翻转奇偶）。

    拼接点必须满足 ``supply(a[p]) == demand(b[q])``，否则会破坏同色有效性。
    优先选择宏代价增量最小的拼接对。
    """
    if not trails:
        return trails
    total = sum(len(t) for t in trails)
    if (total - len(trails)) % 2 == 0:
        return trails

    best = None
    best_delta = None
    for i in range(len(trails)):
        for j in range(i + 1, len(trails)):
            a, b = trails[i], trails[j]
            head_pos: Dict[str, int] = {}
            for p, e in enumerate(a):
                head_pos.setdefault(e[1], p)
            for q, e in enumerate(b):
                p = head_pos.get(e[0])
                if p is None:
                    continue
                delta = (len(a) + len(b)) // 2 - len(a) // 2 - len(b) // 2
                if best_delta is None or delta < best_delta:
                    best_delta = delta
                    best = (i, j, p, q)
    if best is None:
        return None

    i, j, p, q = best
    a, b = trails[i], trails[j]
    merged = list(a[p + 1:]) + list(a[:p + 1]) + list(b[q:]) + list(b[:q])
    out = [t for k, t in enumerate(trails) if k not in (i, j)]
    out.append(merged)
    return out


def _best_decomposition(
    edges: Counter,
    colors: Sequence[str],
    trials: int,
    seed: int,
    require_even: bool = True,
) -> Optional[List[List[Tuple[str, str]]]]:
    """多次随机分解，取宏数量最少者。

    置换奇偶只取决于循环个数 T：``parity = (W - T) mod 2``（W=错色位置数）。
    偶置换方案优先；若随机分解全为奇，则在共享颜色处拼接两条 trail 翻转奇偶。
    """
    if not edges:
        return []
    total = sum(edges.values())
    best = None
    best_cost = None
    for t in range(trials):
        rng = random.Random((seed * 1000003 + t * 7919) & 0xFFFFFFFF)
        trails = _decompose_trails(edges, colors, rng)
        if require_even and (total - len(trails)) % 2 != 0:
            spliced = _splice_to_even(trails)
            if spliced is None:
                continue
            trails = spliced
        cost = _trail_cost(trails)
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best = trails
    return best


# ---------------------------------------------------------------------------
# trail -> 具体位置循环 -> movement 置换
# ---------------------------------------------------------------------------

def _assign_positions(
    trails: Sequence[Sequence[Tuple[str, str]]],
    positions_by_edge: Dict[Tuple[str, str], List[Tuple[int, int, int]]],
    rng: random.Random,
) -> List[List[Tuple[int, int, int]]]:
    """给每条 trail 的每个边分配一个具体位置（同边位置不重复使用）。"""
    pool: Dict[Tuple[str, str], List[Tuple[int, int, int]]] = {
        k: list(v) for k, v in positions_by_edge.items()
    }
    cycles: List[List[Tuple[int, int, int]]] = []
    for trail in trails:
        cyc = []
        for edge in trail:
            lst = pool[edge]
            idx = rng.randrange(len(lst))
            cyc.append(lst.pop(idx))
        cycles.append(cyc)
    return cycles


def _cycles_to_movement(
    cycles: Sequence[Sequence[Tuple[int, int, int]]],
    dense_of_pos,
    n: int = 24,
) -> List[int]:
    g = list(range(n))
    for cyc in cycles:
        length = len(cyc)
        for i in range(length):
            g[dense_of_pos(cyc[i])] = dense_of_pos(cyc[(i + 1) % length])
    return g


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def _primitive_for(orbit: CenterOrbitKind) -> CenterPrimitive:
    return CORNER_MAIN if orbit == CenterOrbitKind.CORNER else EDGE_MAIN


def _primitives_for(orbit: CenterOrbitKind) -> Tuple[CenterPrimitive, ...]:
    """该轨道的主/备用基元；两者对同一有序三重产生同向 3-cycle，取 setup 最短者。"""
    if orbit == CenterOrbitKind.CORNER:
        return (CORNER_MAIN, CORNER_BACKUP)
    return (EDGE_MAIN, EDGE_BACKUP)


def _solve_orbit_color(
    working: Cube5,
    orbit: CenterOrbitKind,
    face_color: Dict[str, str],
    moves: List[str],
    trials: int,
    seed: int,
    primitives: Optional[Tuple[CenterPrimitive, ...]] = None,
) -> Tuple[int, bool]:
    """对单轨道做同色等价求解，把宏追加进 moves。返回 (宏数, 是否已归色)。"""
    wrong = _wrong_positions(working, orbit, face_color)
    if not wrong:
        return 0, True

    edges = Counter((demand, supply) for _, demand, supply in wrong)
    colors = sorted({c for e in edges for c in e})
    positions_by_edge = _positions_by_edge(wrong)

    trails = _best_decomposition(edges, colors, trials, seed)
    if trails is None:
        return 0, False

    # 多个位置分配里选 setup 最短的一条（用最终宏总长度评分）。
    ids = orbit_global_ids(orbit)
    global_to_dense = {g: i for i, g in enumerate(ids)}

    def dense_of_pos(pos):
        return global_to_dense[CENTER_INDEX[pos]]

    if primitives is None:
        primitives = _primitives_for(orbit)
    tables = [get_setup_table(p) for p in primitives]

    best_plan = None
    best_len = None
    best_macro_count = None
    for attempt in range(4):
        rng = random.Random((seed * 2654435761 + attempt * 40503) & 0xFFFFFFFF)
        cycles = _assign_positions(trails, positions_by_edge, rng)
        g = _cycles_to_movement(cycles, dense_of_pos, 24)
        if permutation_parity(g) != 0:
            continue
        triples = decompose_even_pos_to_home(tuple(g))
        total = 0
        plan: List[List[str]] = []
        for trip in triples:
            target = tuple(ids[x] for x in trip)
            macro = min(
                (instantiate_center_3cycle(p, target, tbl)
                 for p, tbl in zip(primitives, tables)),
                key=len,
            )
            plan.append(macro)
            total += len(macro)
        if best_len is None or total < best_len:
            best_len = total
            best_plan = plan
            best_macro_count = len(plan)

    if best_plan is None:
        return 0, False

    for macro in best_plan:
        working.apply_moves(macro)
        moves.extend(macro)
    return best_macro_count, True


def solve_centers5_color(
    cube: Cube5,
    trials: int = 240,
    seed: int = 0,
) -> CenterSolveResult:
    """同色等价求解中心。失败时 success=False，调用方可回退精确求解。"""
    original = cube.clone()
    working = cube.clone()
    moves: List[str] = []

    face_color = _face_colors(working)

    corner_perm = build_pos_to_home_permutation(working, CenterOrbitKind.CORNER)
    edge_perm = build_pos_to_home_permutation(working, CenterOrbitKind.EDGE)
    initial_corner_parity = permutation_parity(corner_perm)
    initial_edge_parity = permutation_parity(edge_perm)

    corner_count = 0
    edge_count = 0
    for orbit_index, orbit in enumerate(_ACTIVE_ORBITS):
        prims = (EDGE_COMM4,) if orbit == CenterOrbitKind.EDGE else None
        count, ok = _solve_orbit_color(
            working, orbit, face_color, moves, trials, seed * 131 + orbit_index,
            primitives=prims,
        )
        if not ok:
            return CenterSolveResult(
                success=False, moves=tuple(moves),
                initial_corner_parity=initial_corner_parity,
                initial_edge_parity=initial_edge_parity,
                parity_prefix=(),
                corner_cycle_count=corner_count, edge_cycle_count=edge_count,
                setup_cache_hits=0, setup_cache_builds=0,
                error_code=CENTER_COLOR_SOLVE_FAILED,
                message="轨道 %s 同色分解失败" % orbit.value,
            )
        if orbit == CenterOrbitKind.CORNER:
            corner_count = count
        else:
            edge_count = count

    # 重放校验：中心按颜色归面。
    replay = original.clone()
    replay.apply_moves(moves)
    if not _all_centers_color_solved(replay):
        return CenterSolveResult(
            success=False, moves=tuple(moves),
            initial_corner_parity=initial_corner_parity,
            initial_edge_parity=initial_edge_parity,
            parity_prefix=(),
            corner_cycle_count=corner_count, edge_cycle_count=edge_count,
            setup_cache_hits=0, setup_cache_builds=0,
            error_code=CENTER_REPLAY_MISMATCH,
            message="同色求解重放后中心未按颜色归面",
        )

    assert_legal_5x5_solution_moves(moves)

    return CenterSolveResult(
        success=True, moves=tuple(moves),
        initial_corner_parity=initial_corner_parity,
        initial_edge_parity=initial_edge_parity,
        parity_prefix=(),
        corner_cycle_count=corner_count, edge_cycle_count=edge_count,
        setup_cache_hits=0, setup_cache_builds=0,
        message="中心同色求解（%d + %d 宏）" % (corner_count, edge_count),
    )


def _all_centers_color_solved(cube: Cube5) -> bool:
    face_color = _face_colors(cube)
    for cubie in cube.cubies.values():
        if len(cubie.stickers) != 1:
            continue
        face = _face_of_position(cubie.pos)
        if face is None or face_color.get(face) != _single_color(cubie):
            return False
    return True
