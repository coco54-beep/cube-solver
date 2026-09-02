"""Probe the 4x4 center-permutation group to choose a solver design.
English-only output (console-encoding safe).

Answers:
  1) cycle structure + parity of each base move (wide and whole).
  2) reachable-state growth by depth (gauges group size / diameter).
  3) "clean" primitives reachable: single 3-cycles (support 3) and
     double 3-cycles (support 6, two 3-cycles) -> the golden building blocks.
"""
from collections import deque

from cube.cube4 import Cube4

CENTER_HOMES = {
    "U": [(1, 3, 1), (1, 3, -1), (-1, 3, 1), (-1, 3, -1)],
    "D": [(1, -3, 1), (1, -3, -1), (-1, -3, 1), (-1, -3, -1)],
    "F": [(1, 1, 3), (1, -1, 3), (-1, 1, 3), (-1, -1, 3)],
    "B": [(1, 1, -3), (1, -1, -3), (-1, 1, -3), (-1, -1, -3)],
    "R": [(3, 1, 1), (3, 1, -1), (3, -1, 1), (3, -1, -1)],
    "L": [(-3, 1, 1), (-3, 1, -1), (-3, -1, 1), (-3, -1, -1)],
}
ALL_CENTERS = [h for f in ("U", "D", "F", "B", "R", "L") for h in CENTER_HOMES[f]]
SLOT_INDEX = {p: i for i, p in enumerate(ALL_CENTERS)}
SLOT_FACE = [None] * 24
for i, p in enumerate(ALL_CENTERS):
    (x, y, z) = p
    if abs(x) == 3:
        SLOT_FACE[i] = "R" if x > 0 else "L"
    elif abs(y) == 3:
        SLOT_FACE[i] = "U" if y > 0 else "D"
    else:
        SLOT_FACE[i] = "F" if z > 0 else "B"

FACES = ["U", "D", "F", "B", "R", "L"]
SOLVED = tuple(range(24))


def base_perm(face, is_wide, ccw=False):
    mv = (face.lower() if is_wide else face) + ("'" if ccw else "")
    cube = Cube4.solved()
    cube.apply_move(mv)
    p = [0] * 24
    for cub in cube.cubies.values():
        if len(cub.stickers) != 1:
            continue
        p[SLOT_INDEX[cub.home]] = SLOT_INDEX[cub.pos]
    return tuple(p)


MOVES = {}
for f in FACES:
    for wide in (False, True):
        for ccw in (False, True):
            label = (f.lower() if wide else f) + ("'" if ccw else "")
            MOVES[label] = base_perm(f, wide, ccw)


def apply_perm(state, perm):
    return tuple(perm[s] for s in state)


def cycle_lengths(perm):
    seen = set()
    out = []
    for s in range(24):
        if s in seen:
            continue
        c = 0
        cur = s
        while cur not in seen:
            seen.add(cur)
            c += 1
            cur = perm[cur]
        if c > 1:
            out.append(c)
    return sorted(out, reverse=True)


def support_size(perm):
    return sum(1 for s in range(24) if perm[s] != s)


def parity(perm):
    # sign via cycle lengths: even iff (24 - num_cycles) odd... use transpositions
    seen = set()
    trans = 0
    for s in range(24):
        if s in seen:
            continue
        c = 0
        cur = s
        while cur not in seen:
            seen.add(cur)
            c += 1
            cur = perm[cur]
        trans += c - 1
    return "even" if trans % 2 == 0 else "odd"


def main():
    print("=== base move cycle structure + parity ===")
    for f in FACES:
        for wide in (False, True):
            label = (f.lower() if wide else f)
            pm = MOVES[label]
            print(f"  {label:4s} sup={support_size(pm):2d} cyc={cycle_lengths(pm)} parity={parity(pm)}")

    labels = list(MOVES.keys())

    # BFS from solved: growth by depth + collect clean primitives.
    print("\n=== BFS growth + clean primitives (single/double 3-cycles) ===")
    visited = {SOLVED: (None, None)}
    frontier = deque([SOLVED])
    depth = 0
    single3 = {}
    double3 = {}
    while frontier and depth < 5:
        depth += 1
        nxt = []
        for st in frontier:
            for lab in labels:
                ns = apply_perm(st, MOVES[lab])
                if ns in visited:
                    continue
                visited[ns] = (st, lab)
                nxt.append(ns)
                sup = support_size(ns)
                cl = cycle_lengths(ns)
                if sup == 3 and cl == [3]:
                    single3[ns] = (st, lab)
                elif sup == 6 and cl == [3, 3]:
                    double3[ns] = (st, lab)
        frontier = deque(nxt)
        print(f"  depth {depth}: frontier={len(nxt):7d}  total_visited={len(visited):9d}")

    def reconstruct(state):
        seq = []
        node = state
        while visited[node][0] is not None:
            node, lab = visited[node]
            seq.append(lab)
        seq.reverse()
        return seq

    print(f"\n  single 3-cycles found (depth<=5): {len(single3)}")
    for ns in list(single3)[:12]:
        print(f"    sup={support_size(ns)} faces={sorted(set(SLOT_FACE[s] for s in range(24) if ns[s]!=s))} seq={' '.join(reconstruct(ns))}")
    print(f"  double 3-cycles found (depth<=5): {len(double3)}")
    for ns in list(double3)[:12]:
        sup = [s for s in range(24) if ns[s] != s]
        print(f"    faces={sorted(set(SLOT_FACE[s] for s in sup))} seq={' '.join(reconstruct(ns))}")


if __name__ == "__main__":
    main()
