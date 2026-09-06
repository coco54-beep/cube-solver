"""模式数据库 + IDA* 攻克深打乱（Milestone 2.5 方向 PDB）。

PDB 维度：目标色对 3 个成员（1 中 + 2 翼）各自实际棱位置 (m_pos, w1_pos, w2_pos)。
目标 = 三者同槽。反向 BFS 建 PDB，d(m,w1,w2) = 三者聚到某同槽的最小步数 → 可采纳下界 h_edge。
IDA* 用 f = g + h_edge 迭代加深，精确找最短解（不靠 beam、不丢路径）。

中心维度暂以可采纳下界 0 处理（h_edge 不依赖中心，仍是下界）。
测量 len 6 / 8 / 10 命中率与解长。
"""

import os
import sys
import time
from collections import deque

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import random

from cube.cube5 import Cube5

from solver.edge5.compact_state import (
    MOVES,
    MOVE_TABLES,
    _SLOT_MID,
    _SLOT_WINGS,
    color_off,
    matched,
    state_of,
    step,
    work_paired,
    target_home_slot,
)
from solver.edge5.positions import (
    MIDDLE_ORDER,
    WING_ORDER,
    SLOT_NAMES,
    color_pair_of_slot,
    slot_of,
)
from solver.edge5.state import face_colors


def _scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def _inv_perm(perm):
    inv = [0] * len(perm)
    for j, p in enumerate(perm):
        inv[p] = j
    return tuple(inv)


_MPOS_SLOT = [slot_of(MIDDLE_ORDER[m]) for m in range(12)]
_WPOS_SLOT = [slot_of(WING_ORDER[w]) for w in range(24)]
_PM = {mv: MOVE_TABLES[mv][0] for mv in MOVES}
_PW = {mv: MOVE_TABLES[mv][1] for mv in MOVES}
_PM_INV = {mv: _inv_perm(_PM[mv]) for mv in MOVES}
_PW_INV = {mv: _inv_perm(_PW[mv]) for mv in MOVES}


def build_pdb():
    """d[(m_pos, w1_pos, w2_pos)] = 三者聚同槽的最小步数。"""
    goal = []
    for m in range(12):
        mslot = _MPOS_SLOT[m]
        for w1 in range(24):
            if _WPOS_SLOT[w1] != mslot:
                continue
            for w2 in range(24):
                if _WPOS_SLOT[w2] != mslot:
                    continue
                goal.append((m, w1, w2))
    dist = {}
    dq = deque()
    for g in goal:
        dist[g] = 0
        dq.append(g)
    while dq:
        m, w1, w2 = dq.popleft()
        d = dist[(m, w1, w2)]
        nd = d + 1
        for mv in MOVES:
            key = (_PM_INV[mv][m], _PW_INV[mv][w1], _PW_INV[mv][w2])
            if key in dist:
                continue
            dist[key] = nd
            dq.append(key)
    return dist


def _member_positions(state, tgt_home):
    tmid = _SLOT_MID[tgt_home]
    mpos = None
    for j, v in enumerate(state.middle):
        if v == tmid:
            mpos = j
            break
    tw1, tw2 = _SLOT_WINGS[tgt_home]
    wps = []
    for j, v in enumerate(state.wing):
        if v in (tw1, tw2):
            wps.append(j)
    if len(wps) != 2 or mpos is None:
        return None
    return (mpos, wps[0], wps[1])


def _h_edge(state, dist, tgt_home):
    mp = _member_positions(state, tgt_home)
    if mp is None:
        return 0
    return dist.get(mp, 999)


def _h(state, dist, tgt_home):
    """可采纳启发式：edge 汇聚下界 与 中心归面粗下界 取 max。"""
    he = _h_edge(state, dist, tgt_home)
    hc = color_off(state) // 10
    return he if he > hc else hc


def _is_goal(state, tgt_home, work_slot):
    return matched(state, tgt_home, work_slot) == 3 \
        and work_paired(state, work_slot) and color_off(state) == 0


def _dfs(state, g, limit, dist, tgt_home, work_slot, path, found, ctx):
    ctx["nodes"] += 1
    if ctx["nodes"] % 200000 == 0 and time.time() - ctx["t0"] > ctx["time_cap"]:
        ctx["abort"] = True
        return "ABORT"
    if ctx["abort"]:
        return "ABORT"
    f = g + _h(state, dist, tgt_home)
    if f > limit:
        return f
    if _is_goal(state, tgt_home, work_slot):
        found.append(list(path))
        return "FOUND"
    mn = sys.maxsize
    last_face = None
    for mv in MOVES:
        face = mv.lstrip("0123456789")[0]
        if face == last_face:
            continue
        ns = step(state, mv)
        path.append(mv)
        t = _dfs(ns, g + 1, limit, dist, tgt_home, work_slot, path, found, ctx)
        path.pop()
        if t == "FOUND":
            return "FOUND"
        if t == "ABORT":
            return "ABORT"
        if t < mn:
            mn = t
        last_face = face
    return mn


def ida_star(cube, target, work_slot, dist, time_cap):
    original = cube.clone()
    tgt_home = target_home_slot(original, target)
    if tgt_home is None:
        return None, 0, 0
    start = state_of(original)
    if _is_goal(start, tgt_home, work_slot):
        return [], 0, 0
    ctx = {"t0": time.time(), "time_cap": time_cap, "nodes": 0, "abort": False}
    limit = _h(start, dist, tgt_home)
    while limit < sys.maxsize:
        found = []
        t = _dfs(start, 0, limit, dist, tgt_home, work_slot, [], found, ctx)
        if t == "FOUND":
            return found[0], ctx["nodes"], 1
        if ctx["abort"] or t == "ABORT":
            return None, ctx["nodes"], 1
        if t == sys.maxsize:
            return None, ctx["nodes"], 1
        limit = t
    return None, ctx["nodes"], 1


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--length", type=int, default=6)
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--time-cap", type=float, default=25)
    args = ap.parse_args()

    t0 = time.time()
    dist = build_pdb()
    print(f"PDB 大小={len(dist)} 建/持有 耗时{time.time()-t0:.1f}s")

    rng = random.Random(args.seed)
    ok = 0
    for i in range(args.n):
        cube = Cube5.solved()
        _scramble(cube, args.length, rng)
        fc = face_colors(cube)
        work_slot = rng.choice(SLOT_NAMES)
        target = color_pair_of_slot(work_slot, fc)
        t1 = time.time()
        path, nodes, _ = ida_star(cube, target, work_slot, dist, args.time_cap)
        if path is not None:
            ok += 1
            print(f"  case{i}: 命中 解长={len(path)} nodes={nodes} 耗时{time.time()-t1:.1f}s")
        else:
            print(f"  case{i}: 未命中/超时 nodes={nodes} 耗时{time.time()-t1:.1f}s")
    print(f"len={args.length}  success={ok}/{args.n}")


if __name__ == "__main__":
    main()
