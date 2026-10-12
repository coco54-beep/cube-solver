"""Two-phase optimal solver for the order-3 Mirror Tower.

Phase 1 solves the 24 movable markers with a full God's-algorithm table
(11520x324). Phase 2 fixes the fixed centres with a small table of group
elements that leave the movable markers untouched. Assets are produced by
scripts/build_mirror_tower_tables.py.
"""
from collections import deque
from functools import lru_cache
import json
import zlib
from pathlib import Path

from cube.mirror_tower import marker_system
from cube.polyhedral import Move

_TABLE_PATH = Path(__file__).parent / "data" / "mirror_tower_table.bin"
_CENTERS_PATH = Path(__file__).parent / "data" / "mirror_tower_centers.json"


def reach(stickers, perms):
    start = tuple(stickers)
    seen = {start}
    queue = deque([start])
    while queue:
        st = queue.popleft()
        for p in perms:
            nx = tuple(p[v] for v in st)
            if nx not in seen:
                seen.add(nx)
                queue.append(nx)
    return {cfg: i for i, cfg in enumerate(sorted(seen))}


@lru_cache(maxsize=1)
def model():
    points, _, virtual = marker_system()
    order = virtual.spec.turn_order
    moves = tuple(Move(a, l, amt) for a in range(len(virtual.spec.axes))
                  for l in range(len(virtual.layers[a])) for amt in range(1, order))
    perms = tuple(virtual.permutation(m) for m in moves)
    byorb = {}
    for i, (o, p, f) in enumerate(points):
        byorb.setdefault(o, []).append(i)
    o0, o1, o2 = byorb[0], byorb[1], byorb[2]
    rank0 = reach(o0, perms)
    rank1 = reach(o1, perms)
    rank2 = reach(o2, perms)
    return moves, perms, rank0, rank1, rank2


@lru_cache(maxsize=1)
def _tables():
    table = zlib.decompress(_TABLE_PATH.read_bytes())
    centers = json.loads(_CENTERS_PATH.read_text(encoding="utf-8"))
    return table, centers


def solve_mirror_tower(cube, cancel=None, progress=None):
    if cube.is_solved():
        return ()
    moves, perms, rank0, rank1, rank2 = model()
    n0, n1 = len(rank0), len(rank1)
    table, centers = _tables()

    def moving_index(st):
        return rank1[st[12:24]] * n0 + rank0[st[0:12]]

    def center_index(st):
        return rank2[st[24:36]]

    st = tuple(cube.labeled_state())
    goal = tuple(range(36))
    word = []
    dist = table[moving_index(st)]
    while dist > 0:
        if cancel and cancel():
            raise InterruptedError()
        for mi, p in enumerate(perms):
            nx = tuple(p[v] for v in st)
            if table[moving_index(nx)] == dist - 1:
                st = nx
                word.append(mi)
                dist -= 1
                break
        else:
            raise ValueError("Mirror tower phase-1 descent failed")
    # Phase 2: fix centres with a movable-marker-preserving word.
    entry = centers.get(str(center_index(st)))
    if entry is None:
        from cube.mirror_tower import solve_mirror_tower as fallback
        return fallback(cube, cancel, progress)
    inverse = {}
    for i, m in enumerate(moves):
        inverse[i] = next(j for j, m2 in enumerate(moves) if m2 == m.inverse(3))
    for mi in reversed(entry):
        word.append(inverse[mi])
    solution = tuple(moves[mi] for mi in word)
    replay = cube.clone()
    for move in solution:
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError("Mirror tower solution did not restore its shape")
    return solution
