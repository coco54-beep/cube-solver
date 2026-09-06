"""A* / 最佳优先搜索：目标 = 目标棱 3 块聚工作槽 + 中心 color_solved（Milestone 2.5 诊断）。

用可行启发式 h = (3 - matched) + color_off 下界。A* 不按固定宽度修剪而是按 f 展开，
适合"解短"问题（实验显示 len-6 打乱可达解长仅 5）。测量 len 6 / 8 能否在节点预算内命中。
"""

import os
import sys
import time
import heapq

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import random

from cube.cube5 import Cube5

from solver.edge5.compact_state import (
    MOVES,
    color_off,
    matched,
    state_of,
    step,
    work_paired,
    target_home_slot,
)
from solver.edge5.positions import SLOT_NAMES, color_pair_of_slot
from solver.edge5.state import face_colors


def _scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def _h(st, tgt_home, work_slot):
    return (3 - matched(st, tgt_home, work_slot)) + color_off(st)


def _astar(cube, target, work_slot, node_budget):
    original = cube.clone()
    tgt_home = target_home_slot(original, target)
    if tgt_home is None:
        return None, 0
    start = state_of(original)
    if matched(start, tgt_home, work_slot) == 3 and work_paired(start, work_slot) \
            and color_off(start) == 0:
        return [], 0
    start_key = start.key
    g = {start_key: 0}
    parent = {}
    heap = [(_h(start, tgt_home, work_slot), start_key)]
    came = {start_key: None}
    nodes = 0
    while heap:
        f, skey = heapq.heappop(heap)
        nodes += 1
        if nodes > node_budget:
            return None, nodes
        # 重建 compact state from key
        st = state_of_from_key(skey, original)
        if matched(st, tgt_home, work_slot) == 3 and work_paired(st, work_slot) \
                and color_off(st) == 0:
            # 回溯路径
            path = []
            cur = skey
            while came[cur] is not None:
                pkey, mv = came[cur]
                path.append(mv)
                cur = pkey
            path.reverse()
            return path, nodes
        for mv in MOVES:
            ns = step(st, mv)
            nk = ns.key
            ng = g[skey] + 1
            if nk not in g or ng < g[nk]:
                g[nk] = ng
                parent[nk] = skey
                came[nk] = (skey, mv)
                heapq.heappush(heap, (_h(ns, tgt_home, work_slot) + ng, nk))
    return None, nodes


# 从 key 重建 compact state。key 是 (middle,wing,center) 三元组。
def _state_from_key(key):
    from solver.edge5.compact_state import CompactPairingState
    return CompactPairingState(key[0], key[1], key[2])


def state_of_from_key(key, original):
    return _state_from_key(key)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--length", type=int, default=6)
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--nodes", type=int, default=2000000)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    ok = 0
    for i in range(args.n):
        cube = Cube5.solved()
        _scramble(cube, args.length, rng)
        fc = face_colors(cube)
        work_slot = rng.choice(SLOT_NAMES)
        target = color_pair_of_slot(work_slot, fc)
        t0 = time.time()
        path, nodes = _astar(cube, target, work_slot, args.nodes)
        if path is not None:
            ok += 1
            print(f"  case{i}: 命中 解长={len(path)} nodes={nodes} 耗时{time.time()-t0:.1f}s")
        else:
            print(f"  case{i}: 未命中 nodes={nodes} 耗时{time.time()-t0:.1f}s")
    print(f"len={args.length}  success={ok}/{args.n}")


if __name__ == "__main__":
    main()
