"""4x4 center exploration (English output to avoid console garbling).

Determines what center permutations candidate moves induce, and measures the
reachable center-state space size (decides search vs constructive solver).

Center piece = exactly one coord with abs == 3 (outer ring); it is always on
exactly one face. Goal: each center on its home face.
"""

from collections import deque

from cube.cube4 import Cube4

# 24 center home coords (fixed order): face-major
CENTER_HOMES = {
    "U": [(1, 3, 1), (1, 3, -1), (-1, 3, 1), (-1, 3, -1)],
    "D": [(1, -3, 1), (1, -3, -1), (-1, -3, 1), (-1, -3, -1)],
    "F": [(1, 1, 3), (1, -1, 3), (-1, 1, 3), (-1, -1, 3)],
    "B": [(1, 1, -3), (1, -1, -3), (-1, 1, -3), (-1, -1, -3)],
    "R": [(3, 1, 1), (3, 1, -1), (3, -1, 1), (3, -1, -1)],
    "L": [(-3, 1, 1), (-3, 1, -1), (-3, -1, 1), (-3, -1, -1)],
}
ALL_CENTERS = [h for f in ("U", "D", "F", "B", "R", "L") for h in CENTER_HOMES[f]]
HOME_TO_FACE = {h: f for f, hs in CENTER_HOMES.items() for h in hs}
SLOT_INDEX = {p: i for i, p in enumerate(ALL_CENTERS)}
FACES = ["U", "D", "F", "B", "R", "L"]


def face_of_pos(pos):
    (x, y, z) = pos
    for v, axis in ((x, 0), (y, 1), (z, 2)):
        if abs(v) == 3:
            if axis == 0:
                return "R" if v > 0 else "L"
            if axis == 1:
                return "U" if v > 0 else "D"
            return "F" if v > 0 else "B"
    raise ValueError(f"not a center coord: {pos}")


def base_perm(face, is_wide):
    """Slot permutation of a single 90deg CW turn: p[s] = new slot of piece at slot s.

    Computed by simulating one move on a solved cube. In the solved state piece i
    sits at slot i, so after the move piece i is at slot p[i].
    """
    mv = face.lower() if is_wide else face
    cube = Cube4.solved()
    cube.apply_move(mv)
    p = [0] * 24
    for cub in cube.cubies.values():
        if len(cub.stickers) != 1:
            continue
        i = SLOT_INDEX[cub.home]
        p[i] = SLOT_INDEX[cub.pos]
    return p


def cycles(p):
    seen = set()
    out = []
    for s in range(24):
        if s in seen:
            continue
        cyc = []
        cur = s
        while cur not in seen:
            seen.add(cur)
            cyc.append(cur)
            cur = p[cur]
        if len(cyc) > 1:
            out.append(cyc)
    return out


def describe_move(name, perm):
    cs = cycles(perm)
    moved = sum(len(c) for c in cs)
    faces = sorted({HOME_TO_FACE[ALL_CENTERS[s]] for c in cs for s in c})
    print(f"  {name:6s} moves {moved:2d} centers, cycles={len(cs)}, faces={faces}")


def apply_perm(state, perm):
    return tuple(perm[s] for s in state)


def main():
    print("=== single 90deg turns: center permutation (from solved) ===")
    perms = {}
    for face in FACES:
        perms[(face, False)] = base_perm(face, False)
        perms[(face, True)] = base_perm(face, True)
    for (face, wide), p in perms.items():
        describe_move(f"{face}{'w' if wide else ' '}", p)

    print("\n=== reachable center-state space (group size) ===")
    start = tuple(range(24))  # solved: piece i at slot i
    moves = []
    for p in perms.values():
        p2 = [p[p[s]] for s in range(24)]
        p3 = [p[p2[s]] for s in range(24)]
        moves += [p, p2, p3]

    CAP = 4_000_000
    dist = {start: 0}
    frontier = deque([start])
    count = 1
    maxd = 0
    while frontier and count < CAP:
        st = frontier.popleft()
        d = dist[st]
        for perm in moves:
            ns = apply_perm(st, perm)
            if ns not in dist:
                dist[ns] = d + 1
                if d + 1 > maxd:
                    maxd = d + 1
                count += 1
                frontier.append(ns)
    print(f"  reachable states: {count}  (cap {CAP})  max depth: {maxd}")
    if count >= CAP:
        print("  (hit cap; space larger than cap)")


if __name__ == "__main__":
    main()
