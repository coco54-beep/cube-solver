"""Find short 4x4 center-move sequences achieving a goal, via BFS over the
full 24-center state. Used to discover verified primitives for the
constructive center solver.

State: tuple of 24 ints; state[j] = slot index currently holding piece j.
Slot i is the center position ALL_CENTERS[i] (a fixed position with a fixed
face). A piece is "on" the face of its current slot.
"""

from collections import deque

from cube.cube4 import Cube4
from cube.notation import parse_move_str

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


def base_perm(face, is_wide, ccw=False):
    mv = (face.lower() if is_wide else face) + ("'" if ccw else "")
    cube = Cube4.solved()
    cube.apply_move(mv)
    p = [0] * 24
    for cub in cube.cubies.values():
        if len(cub.stickers) != 1:
            continue
        p[SLOT_INDEX[cub.home]] = SLOT_INDEX[cub.pos]
    return p


# 24 moves: 12 (face,width) x {CW, CCW}
MOVES = []
for f in FACES:
    for wide in (False, True):
        for ccw in (False, True):
            label = (f.lower() if wide else f) + ("'" if ccw else "")
            MOVES.append((label, base_perm(f, wide, ccw)))

SOLVED = tuple(range(24))


def apply_perm(state, perm):
    return tuple(perm[s] for s in state)


def piece_faces(state):
    """piece index -> current face (for all 24 pieces)."""
    return [SLOT_FACE[state[j]] for j in range(24)]


def find_sequence(start, goal_test, max_depth=8, node_cap=2_000_000):
    """BFS; returns list of move labels from start to first state passing goal_test."""
    if goal_test(start):
        return []
    start_parent = {start: (None, None)}
    frontier = deque([start])
    count = 1
    depth_mark = 0
    levels = [start]
    cur_depth = 0
    while levels and cur_depth < max_depth and count < node_cap:
        cur_depth += 1
        nxt = []
        for st in levels:
            for label, perm in MOVES:
                ns = apply_perm(st, perm)
                if ns not in start_parent:
                    start_parent[ns] = (st, label)
                    count += 1
                    nxt.append(ns)
                    if goal_test(ns):
                        # reconstruct
                        seq = []
                        node = ns
                        while start_parent[node][0] is not None:
                            node, lab = start_parent[node]
                            seq.append(lab)
                        seq.reverse()
                        return seq
        levels = nxt
        depth_mark += 1
    return None


def faces_count(state):
    from collections import Counter
    return Counter(piece_faces(state))


if __name__ == "__main__":
    import sys

    # Build a test state: move 2 U-centers off U into the middle layer.
    # Start solved, apply Rw (moves 2 U-centers, 2 D, 2 F, 2 B, 4 R).
    test_start = SOLVED
    for lab, perm in MOVES:
        if lab == "r":
            test_start = apply_perm(test_start, perm)
            break

    pf = piece_faces(test_start)
    print("After Rw (from solved):")
    from collections import Counter
    print("  U-pieces on faces:", [pf[j] for j, h in enumerate(ALL_CENTERS) if SLOT_FACE[j] == "U"])
    print("  face counts:", dict(Counter(pf)))

    # Goal: the 4 U-colored pieces all on U.
    u_pieces = [j for j in range(24) if SLOT_FACE[j] == "U"]

    def goal_u4(state):
        return all(SLOT_FACE[state[j]] == "U" for j in u_pieces)

    print("\nSearching: get 4 U-centers onto U (from a Rw-scrambled state)")
    seq = find_sequence(test_start, goal_u4, max_depth=7)
    if seq is None:
        print("  no solution found within depth 7 / node cap")
    else:
        print("  sequence:", " ".join(seq))
        # verify
        st = test_start
        for lab in seq:
            st = apply_perm(st, dict((m[0], m[1]) for m in MOVES)[lab])
        print("  verify U-pieces on faces:", [SLOT_FACE[st[j]] for j in u_pieces])
