"""Build the two Mirror Tower tables: movable markers + centre fix words."""
import sys
import json
import zlib
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from solver.mirror_tower_optimal import model, _TABLE_PATH, _CENTERS_PATH


def build():
    moves, perms, rank0, rank1, rank2 = model()
    n0, n1, n2 = len(rank0), len(rank1), len(rank2)
    goal = tuple(range(36))

    def moving_index(st):
        return rank1[st[12:24]] * n0 + rank0[st[0:12]]

    def center_index(st):
        return rank2[st[24:36]]

    size = n1 * n0
    table = bytearray([255]) * size
    table[moving_index(goal)] = 0
    queue = deque([goal])
    while queue:
        st = queue.popleft()
        d = table[moving_index(st)]
        for p in perms:
            nx = tuple(p[v] for v in st)
            idx = moving_index(nx)
            if table[idx] == 255:
                table[idx] = d + 1
                queue.append(nx)
    print("phase1 table", size, "max", max(table), flush=True)

    # Phase-2 table: shortest movable-marker-preserving words to each centre
    # state. The subgroup that fixes all 24 movable markers has exactly one
    # orbit of size 27 on the 81 centre states (verified with Schreier-Sims),
    # and the puzzle group is 3,732,480 * 27, so this table is complete: any
    # state solvable in phase 1 leaves its centres inside these 27 states.
    centers = {str(center_index(goal)): []}
    seen = {goal: ()}
    queue = deque([goal])
    bound = 14
    move_bound = 8
    while queue and len(centers) < n2:
        st = queue.popleft()
        word = seen[st]
        if len(word) >= bound:
            continue
        for mi, p in enumerate(perms):
            nx = tuple(p[v] for v in st)
            if nx in seen:
                continue
            if table[moving_index(nx)] > move_bound:
                continue
            seen[nx] = word + (mi,)
            if moving_index(nx) == moving_index(goal):
                ci = str(center_index(nx))
                if ci not in centers:
                    centers[ci] = list(word) + [mi]
            queue.append(nx)
    assert len(centers) == 27, f"expected the full 27-state orbit, got {len(centers)}"
    print("centre states", len(centers), "of", n2, flush=True)
    _TABLE_PATH.write_bytes(zlib.compress(bytes(table), 9))
    _CENTERS_PATH.write_text(json.dumps(centers, separators=(",", ":")), encoding="utf-8")
    print("Saved", _TABLE_PATH.stat().st_size, _CENTERS_PATH.stat().st_size, flush=True)


if __name__ == "__main__":
    build()
