"""M2.5 验收基准：穿谷分桶 beam 单棱构造在各类打乱长度下的成功率。

用法：
    python tools/research/5x5/benchmark_single_edge.py [--lengths 1,3,5,8,10,15] [--n 10] [--seed 0]
"""

import argparse
import os
import random
import sys
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cube.cube5 import Cube5
from solver.edge5 import (
    EDGE5_MOVES,
    SearchLimits,
    pair_single_edge_valley,
)
from solver.edge5.state import centers_are_color_solved, is_edge_paired
from solver.edge5.positions import color_pair_of_slot, SLOT_NAMES


def scramble(cube, length, rng):
    moves = list(EDGE5_MOVES)
    prev = None
    for _ in range(length):
        mv = rng.choice(moves)
        # 避免同面连续，让打乱更「一般」。
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(moves)
        cube.apply_move(mv)
        prev = mv


def pick_target(cube, rng):
    """随机挑一个工作槽，取其目标色对。"""
    work_slot = rng.choice(SLOT_NAMES)
    fc = _face_colors(cube)
    target = color_pair_of_slot(work_slot, fc)
    return target, work_slot


def _face_colors(cube):
    from solver.edge5.state import face_colors
    return face_colors(cube)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lengths", default="1,3,5,8,10,15")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-depth", type=int, default=40)
    ap.add_argument("--max-nodes", type=int, default=2000000)
    ap.add_argument("--beam-width", type=int, default=400)
    ap.add_argument("--per-bucket", type=int, default=40)
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    lengths = [int(x) for x in args.lengths.split(",")]
    rng = random.Random(args.seed)
    limits = SearchLimits(
        max_nodes=args.max_nodes, max_depth=args.max_depth,
        timeout_seconds=args.timeout, beam_width=args.beam_width,
        per_bucket=args.per_bucket,
    )

    for length in lengths:
        ok = 0
        total = args.n
        times = []
        fail_codes = {}
        for i in range(total):
            cube = Cube5.solved()
            scramble(cube, length, rng)
            target, work_slot = pick_target(cube, rng)
            t0 = time.monotonic()
            res = pair_single_edge_valley(cube, target, work_slot, limits)
            dt = time.monotonic() - t0
            times.append(dt)
            if res.success:
                # 重放校验：从打乱后的状态出发应用动作，而非从 solved 出发。
                replay = cube.clone()
                replay.apply_moves(res.moves)
                if (is_edge_paired(replay, work_slot)
                        and centers_are_color_solved(replay)):
                    ok += 1
                else:
                    fail_codes["VERIFY_FAIL"] = fail_codes.get("VERIFY_FAIL", 0) + 1
            else:
                fail_codes[res.error_code] = fail_codes.get(res.error_code, 0) + 1
        avg_t = sum(times) / len(times) if times else 0
        print(f"len={length:3d}  success={ok}/{total} "
              f"({100.0*ok/total:5.1f}%)  avg_time={avg_t:.2f}s  fails={fail_codes}")


if __name__ == "__main__":
    main()
