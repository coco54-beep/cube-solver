"""端到端降阶可行性原型（M3-M8 前置验证）：中心解 + 逐棱配对 + 全配对检查。

流程：打乱 -> solve_centers5 -> 对每个逻辑槽依次 pair_single_edge_valley ->
检查是否 all_edges_paired。这是「顺序单棱配对能否收敛到全配对」的决定性实验。

用法：python prototype_reduction.py <length> <n> [seed]
"""

import os
import sys
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import random

from cube.cube5 import Cube5

from solver.center5 import solve_centers5
from solver.edge5.single_edge import pair_single_edge_valley, SearchLimits
from solver.edge5.state import (
    face_colors,
    all_edges_paired,
    paired_count,
    is_edge_paired,
)
from solver.edge5.positions import SLOT_NAMES, color_pair_of_slot
from solver.edge5.compact_state import MOVES


def _scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def main():
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    rng = random.Random(seed)
    limits = SearchLimits(max_nodes=6_000_000, timeout_seconds=60,
                          max_depth=150, beam_width=1500, per_bucket=60)

    all_ok = 0
    for i in range(n):
        cube = Cube5.solved()
        _scramble(cube, length, rng)
        work = cube.clone()
        # 1. 中心
        cr = solve_centers5(work)
        if not cr.success:
            print(f"case{i}: 中心失败 {cr.error_code}")
            continue
        work.apply_moves(cr.moves)
        fc = face_colors(work)
        total_moves = list(cr.moves)
        t0 = time.time()
        # 2. 逐棱
        fail = False
        for slot_name in SLOT_NAMES:
            if is_edge_paired(work, slot_name):
                continue
            target = color_pair_of_slot(slot_name, fc)
            r = pair_single_edge_valley(work, target, slot_name, limits)
            if not r.success:
                print(f"  case{i} slot {slot_name}: 失败 {r.error_code}")
                fail = True
                break
            work.apply_moves(r.moves)
            total_moves.extend(r.moves)
        if fail:
            continue
        elapsed = time.time() - t0
        ok = all_edges_paired(work)
        if ok:
            all_ok += 1
        print(f"case{i}: {'全配对OK' if ok else '未全配对'} paired={paired_count(work)}/12 逐棱耗时{elapsed:.1f}s 总步数~{len(total_moves)}")
    print(f"len={length} 全配对成功 {all_ok}/{n}")


if __name__ == "__main__":
    main()
