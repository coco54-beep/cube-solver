"""双向 BFS 测量「目标棱配对 + 中心归面」的真实最短路径长度（Milestone 2.5 诊断）。

正向：从打乱态展开；反向：从目标态集合展开。
双向在有节点预算的 compact 状态空间上做 BFS/beam，相遇于 compact 键并重放验证。

目标态集合生成（反向起点）：对 solved 做"任意外层动作序列"得到的状态，
每条棱配对、中心归面，满足目标（目标棱在某个槽且配对 + 中心 color_off==0）。

用于回答：len 打乱 6 / 8 时，该目标最短需要多深（判断是搜索问题还是解本身太长）。
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
    color_off,
    matched,
    state_of,
    step,
    work_paired,
)
from solver.edge5.positions import SLOT_NAMES, color_pair_of_slot
from solver.edge5.state import face_colors

_OUTER = [m for m in MOVES if not m[:1].isdigit()]


def _inv(mv):
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    if mv.endswith("3"):
        return ""
    return mv + "'"


def _scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def _backward_start_set(work_slot, max_outer):
    """生成反向起点：对 solved 做外层序列，得目标棱配对+中心归面的状态。"""
    solved = state_of(Cube5.solved())
    start = set()
    # 深度 0
    start.add(solved.key)
    frontier = [solved]
    for _ in range(max_outer):
        nf = []
        for st in frontier:
            for o in _OUTER:
                ns = step(st, o)
                if ns.key in start:
                    continue
                if color_off(ns) != 0:
                    continue
                start.add(ns.key)
                nf.append(ns)
        frontier = nf
    return start


def _bidir(cube, target, work_slot, max_outer_backward, depth, node_budget, beam_width=2000,
           moves=None):
    if moves is None:
        moves = MOVES
    from solver.edge5.compact_state import target_home_slot

    original = cube.clone()
    tgt_home = target_home_slot(original, target)
    if tgt_home is None:
        return None, 0

    # 反向起点集合的 compact 键
    backs = _backward_start_set(work_slot, max_outer_backward)
    # 反向 BFS：记录 反向键 -> 到起点的动作后缀（这里记录动作, 以便拼接）
    # 反向是从起点往外走，动作会"离开目标"，相遇时需取逆。
    b_visited = {}
    b_frontier = []
    for key in backs:
        b_visited[key] = ()
    # 把起点态转化为 compact 对象
    st_map = {}  # key -> step 获得的 compact state 不可直接有，需要重新构造
    # 我们通过 b_visited 存 key->路径(离开目标); 相遇时用反向路径逆。

    # 反向展开（用 step 从各起点态往外走）。为能 step，需要 compact 对象。
    # 重建起点 compact 对象：无法从 key 反推（key 就是 middle/wing/center），可直接构造。
    def _from_key(key):
        from solver.edge5.compact_state import CompactPairingState
        return CompactPairingState(key[0], key[1], key[2])

    b_frontier = [(_from_key(k), ()) for k in backs]

    # 迭代式，正反向交替扩展，相遇检查
    f_frontier = [(state_of(original), ())]
    f_visited = {}
    nodes = [0]
    last_len = None

    for d in range(depth):
        # 正向扩展一层
        nf = []
        for st, path in f_frontier:
            for mv in moves:
                nodes[0] += 1
                if nodes[0] > node_budget:
                    break
                ns = step(st, mv)
                np = path + (mv,)
                if ns.key in f_visited:
                    continue
                f_visited[ns.key] = np
                # 相遇检查
                if ns.key in b_visited:
                    # 拼接：正向 path + 反向(inv 反向路径)
                    bpath = b_visited[ns.key]
                    full = list(np) + [ _inv(m) for m in reversed(bpath) ]
                    replay = original.clone()
                    replay.apply_moves(full)
                    s = state_of(replay)
                    if matched(s, tgt_home, work_slot) == 3 and color_off(s) == 0 \
                            and work_paired(s, work_slot):
                        return full, nodes[0]
                    last_len = len(full)
                nf.append((ns, np))
            if nodes[0] > node_budget:
                break
        if nodes[0] > node_budget:
            break
        f_frontier = nf
        # 反向扩展一层（从当前反向 frontier）
        nb = []
        for st, path in b_frontier:
            for mv in moves:
                nodes[0] += 1
                if nodes[0] > node_budget:
                    break
                ns = step(st, mv)
                np = path + (mv,)
                if ns.key in b_visited:
                    continue
                b_visited[ns.key] = np
                if ns.key in f_visited:
                    fpath = f_visited[ns.key]
                    full = list(fpath) + [_inv(m) for m in reversed(np)]
                    replay = original.clone()
                    replay.apply_moves(full)
                    s = state_of(replay)
                    if matched(s, tgt_home, work_slot) == 3 and color_off(s) == 0 \
                            and work_paired(s, work_slot):
                        return full, nodes[0]
                    last_len = len(full)
                nb.append((ns, np))
            if nodes[0] > node_budget:
                break
        if nodes[0] > node_budget:
            break
        b_frontier = nb
        # 剪枝：限制 frontier 大小（beam）
        def _trim_front(frontier, width):
            if len(frontier) <= width:
                return frontier
            scored = sorted(
                frontier,
                key=lambda it: (-matched(it[0], tgt_home, work_slot),
                                color_off(it[0]), len(it[1])))
            return scored[:width]

        def _trim_back(frontier, width):
            if len(frontier) <= width:
                return frontier
            scored = sorted(
                frontier,
                key=lambda it: (color_off(it[0]), len(it[1])))
            return scored[:width]

        f_frontier = _trim_front(f_frontier, beam_width)
        b_frontier = _trim_back(b_frontier, beam_width)

    return None, nodes[0]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--length", type=int, default=6)
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--depth", type=int, default=16)
    ap.add_argument("--back-outer", type=int, default=2)
    ap.add_argument("--nodes", type=int, default=400000)
    ap.add_argument("--beam", type=int, default=2000)
    ap.add_argument("--moveset", default="all",
                    help="all|outer|wide|target")
    args = ap.parse_args()

    all_moves = MOVES
    if args.moveset == "outer":
        moves = [m for m in MOVES if not m[:1].isdigit()]
    elif args.moveset == "wide":
        moves = [m for m in MOVES if m[:1].isdigit()]
    elif args.moveset == "target":
        moves = [m for m in MOVES if not m[:1].isdigit()]
    else:
        moves = all_moves
    print(f"动作集 {args.moveset} 大小 = {len(moves)}")

    rng = random.Random(args.seed)
    ok = 0
    for i in range(args.n):
        cube = Cube5.solved()
        _scramble(cube, args.length, rng)
        fc = face_colors(cube)
        work_slot = rng.choice(SLOT_NAMES)
        target = color_pair_of_slot(work_slot, fc)
        t0 = time.time()
        path, nodes = _bidir(cube, target, work_slot, args.back_outer, args.depth, args.nodes, args.beam, moves)
        if path is not None:
            ok += 1
            print(f"  case{i}: 命中 解长={len(path)} nodes={nodes} 耗时{time.time()-t0:.1f}s")
        else:
            print(f"  case{i}: 未命中 nodes={nodes} 耗时{time.time()-t0:.1f}s")
    print(f"len={args.length}  success={ok}/{args.n}")


if __name__ == "__main__":
    main()
