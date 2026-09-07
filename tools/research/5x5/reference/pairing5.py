"""独立 5x5 降阶配棱器（reference oracle 用）。

与 `solver/edge5`（edge5 贪心/beam/宏搜索）**完全独立**的 5x5 棱块配对算法，
移植自 `solver/reduction/edge_pairing.py`（4x4 同构路子），只依赖
`Cube5` + 外层/内层宽转，输出标准记号动作，可本地重放。

原语 P = 2U R U R' F R' F' R 2U'（5x5 上用 `2U` 代替 4x4 的 `u`）在 5x5 上的
翼位置换（实证见 tests）为：
- 一个 8-cycle（U 带 4 组棱翼整体轮换），
- 一个 2-cycle：(6,-3,6) [FR 下翼] 与 (6,3,-6) [BR 上翼] 互换。
它保持中心归面与固定面心，并把整条棱组（两翼成对）整体搬动、不拆散已配组。
因此用「外层 setup + P + 逆 setup」可交换任意两个翼位。

仅用于研究 oracle。**不依赖** `solver/edge5` 的搜索类。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from cube.cube5 import Cube5
from cube.coordinates import TURNS, is_in_layer
from cube.notation import parse_move_str, suffix_for_count
from solver.edge5.positions import (
    WING_ORDER,
    slot_of,
    edge_type_of_cubie,
)

Coord = Tuple[int, int, int]

# 12 个棱槽（每个槽 = 该棱对应的两个翼位坐标）。
SLOTS: Dict[str, Tuple[Coord, ...]] = {
    "UF": ((-3, 6, 6), (3, 6, 6)),
    "UR": ((6, 6, -3), (6, 6, 3)),
    "UB": ((-3, 6, -6), (3, 6, -6)),
    "UL": ((-6, 6, -3), (-6, 6, 3)),
    "DF": ((-3, -6, 6), (3, -6, 6)),
    "DR": ((6, -6, -3), (6, -6, 3)),
    "DB": ((-3, -6, -6), (3, -6, -6)),
    "DL": ((-6, -6, -3), (-6, -6, 3)),
    "FR": ((6, -3, 6), (6, 3, 6)),
    "BR": ((6, -3, -6), (6, 3, -6)),
    "FL": ((-6, -3, 6), (-6, 3, 6)),
    "BL": ((-6, -3, -6), (-6, 3, -6)),
}

OUTER = ["R", "R'", "R2", "L", "L'", "L2", "U", "U'", "U2",
         "D", "D'", "D2", "F", "F'", "F2", "B", "B'", "B2"]

# 原语 P（5x5：用小写 u 表示 2 层宽 U，parse_move_full 也接受 2U）。
P: List[str] = ["u", "R", "U", "R'", "F", "R'", "F'", "R", "u'"]

# P 交换的两个翼位（setup 目标）：FR 下翼 与 BR 上翼（实证见模块说明）。
_FR_BOTTOM = (6, -3, 6)
_BR_TOP = (6, 3, -6)


def _p_wing_perm() -> Dict[Coord, Coord]:
    cube = Cube5.solved()
    for m in P:
        cube.apply_move(m)
    return {p: c.home for p, c in cube.cubies.items()
            if len(c.stickers) == 2 and p in WING_ORDER}


_P_WING_PERM = _p_wing_perm()

WINGS = list(WING_ORDER)


def _build_pos_table() -> Dict[str, Dict[Coord, Coord]]:
    table = {}
    for mv in OUTER:
        label, is_wide, count = parse_move_str(mv)
        rot = TURNS[label]
        tbl = {}
        for p in WINGS:
            if is_in_layer(5, label, False, p):
                q = p
                for _ in range(count):
                    q = rot(*q)
                tbl[p] = q
            else:
                tbl[p] = p
        table[mv] = tbl
    return table


_POS_TBL = _build_pos_table()


def _move_pos(mv: str, p: Coord) -> Coord:
    return _POS_TBL[mv][p]


def _inv_of(mv: str) -> str:
    label, is_wide, count = parse_move_str(mv)
    return label + suffix_for_count((4 - count) % 4)


def _apply(cube, moves: List[str]) -> None:
    for m in moves:
        cube.apply_move(m)


def _wing_id(cube) -> Dict[Coord, frozenset]:
    return {p: edge_type_of_cubie(cube.cubies[p])
            for p in WING_ORDER if cube.cubies.get(p) is not None
            and len(cube.cubies[p].stickers) == 2}


def matched_slots(cube) -> int:
    wa = _wing_id(cube)
    by = defaultdict(list)
    for p, i in wa.items():
        by[slot_of(p)].append(i)
    return sum(1 for ids in by.values() if len(ids) == 2 and ids[0] == ids[1])


def edges_paired(cube) -> bool:
    return matched_slots(cube) == 12


def _find_setup_pair(
    a: Coord,
    b: Coord,
    goal: Optional[Tuple[Coord, Coord]] = None,
    cap: int = 8,
) -> Optional[List[str]]:
    if goal is None:
        goal = (_FR_BOTTOM, _BR_TOP)
    start = (a, b)
    if start == goal:
        return []
    fp = {start: None}
    fm = {start: None}
    bp = {goal: None}
    bm = {goal: None}
    f_f = [start]
    b_f = [goal]

    def _meet(st, fp_, fm_, bm_, bp_):
        fwd = []
        cur = st
        while fm_[cur] is not None:
            fwd.append(fm_[cur])
            cur = fp_[cur]
        fwd.reverse()
        bwd = []
        cur = st
        while bm_[cur] is not None:
            bwd.append(_inv_of(bm_[cur]))
            cur = bp_[cur]
        return fwd + bwd

    for _ in range(cap):
        nf = []
        for st in f_f:
            pa, pb = st
            for mv in OUTER:
                ns = (_move_pos(mv, pa), _move_pos(mv, pb))
                if ns in fp:
                    continue
                fp[ns] = st
                fm[ns] = mv
                nf.append(ns)
        f_f = nf
        for st in f_f:
            if st in bp:
                return _meet(st, fp, fm, bm, bp)
        nb = []
        for st in b_f:
            pa, pb = st
            for mv in OUTER:
                ns = (_move_pos(mv, pa), _move_pos(mv, pb))
                if ns in bp:
                    continue
                bp[ns] = st
                bm[ns] = mv
                nb.append(ns)
        b_f = nb
    return None


def _find_best_setup(a: Coord, b: Coord, cap: int = 8) -> Optional[List[str]]:
    best = None
    for goal in ((_FR_BOTTOM, _BR_TOP), (_BR_TOP, _FR_BOTTOM)):
        seq = _find_setup_pair(a, b, goal=goal, cap=cap)
        if seq is None:
            continue
        if best is None or len(seq) < len(best):
            best = seq
    return best


def _compress_log(moves: List[str]) -> List[str]:
    stacked = []
    for m in moves:
        label, is_wide, count = parse_move_str(m)
        key = (label, is_wide)
        while stacked and stacked[-1][0] == key:
            prev_count = stacked[-1][1]
            count = (prev_count + count) % 4
            stacked.pop()
        if count != 0:
            stacked.append((key, count))
    out = []
    for (label, is_wide), count in stacked:
        base = label.lower() if is_wide else label
        out.append(base + suffix_for_count(count))
    return out


def _swap_positions(
    cube,
    a: Coord,
    b: Coord,
    log: List[str],
    setup: Optional[List[str]] = None,
) -> bool:
    if setup is None:
        setup = _find_best_setup(a, b)
    if setup is None:
        return False
    log.extend(setup)
    log.extend(P)
    log.extend([_inv_of(m) for m in reversed(setup)])
    _apply(cube, setup)
    _apply(cube, P)
    _apply(cube, [_inv_of(m) for m in reversed(setup)])
    return True


def matched_set(wa: Dict) -> set:
    by = defaultdict(list)
    for p, g in wa.items():
        by[slot_of(p)].append(g)
    return {s for s, ids in by.items() if len(ids) == 2 and ids[0] == ids[1]}


def _simulate_swap_gain(wa: Dict, setup) -> int:
    m = dict(wa)
    for mv in setup:
        tbl = _POS_TBL[mv]
        m = {tbl.get(p, p): g for p, g in m.items()}
    m = {_P_WING_PERM.get(p, p): g for p, g in m.items()}
    for mv in reversed(setup):
        tbl = _POS_TBL[_inv_of(mv)]
        m = {tbl.get(p, p): g for p, g in m.items()}
    by = defaultdict(list)
    for p, g in m.items():
        by[slot_of(p)].append(g)
    after = sum(1 for ids in by.values() if len(ids) == 2 and ids[0] == ids[1])
    return after - len(matched_set(wa))


def _candidate_swaps(cube, log):
    wa = _wing_id(cube)
    by_slot = defaultdict(list)
    for p, _i in wa.items():
        by_slot[slot_of(p)].append(p)
    paired = {s: (len(ps) == 2 and wa[ps[0]] == wa[ps[1]]) for s, ps in by_slot.items()}

    by_group_unpaired = defaultdict(list)
    for s, ps in by_slot.items():
        if paired[s]:
            continue
        for p in ps:
            by_group_unpaired[wa[p]].append(p)

    out = []
    for A in by_slot:
        if paired[A]:
            continue
        ps = by_slot[A]
        for keep, swap_out in ((ps[0], ps[1]), (ps[1], ps[0])):
            for other in by_group_unpaired.get(wa[keep], []):
                if slot_of(other) == A:
                    continue
                setup = _find_best_setup(swap_out, other, cap=8)
                if setup is None:
                    continue
                gain = _simulate_swap_gain(wa, setup)
                if gain < 1:
                    continue
                seq = setup + list(P) + [_inv_of(m) for m in reversed(setup)]
                out.append((gain, len(_compress_log(log + seq)), len(setup),
                            setup, swap_out, other))
    out.sort(key=lambda t: (-t[0], t[1], t[2]))
    return out


def pair_edges(cube, max_swaps: int = 60, ) -> List[str]:
    """配对 12 个棱组（两翼），返回动作序列；不修改输入。"""
    work = cube.clone()
    log: List[str] = []
    for _ in range(max_swaps):
        if edges_paired(work):
            break
        cands = _candidate_swaps(work, log)
        if not cands:
            break
        _, _, _, setup, ypos, other = cands[0]
        if not _swap_positions(work, ypos, other, log, setup=setup):
            break
        log[:] = _compress_log(log)
    return log


def solve_wing_pairs(cube) -> List[str]:
    moves = pair_edges(cube)
    check = cube.clone()
    check.apply_moves(moves)
    if not edges_paired(check):
        raise ValueError("5x5 wing pairing failed")
    return moves
