"""Detailed 4x4 center discovery: exact slot cycles per move + shortest fix
sequences for the key "last center" situations. English output.

State: tuple state[j] = slot index (0..23) currently holding piece j.
Slot i = fixed center position ALL_CENTERS[i] with fixed face SLOT_FACE[i].
Within a face the 4 slots are interchangeable (same color), so only FACE
assignment matters for the goal.
"""

from collections import deque, Counter
from itertools import product

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
    return p


# 24 moves (label, perm): 6 faces x {single,wide} x {CW,CCW}
MOVES = []
MOVES_BY_LABEL = {}
for f in FACES:
    for wide in (False, True):
        for ccw in (False, True):
            label = (f.lower() if wide else f) + ("'" if ccw else "")
            p = base_perm(f, wide, ccw)
            MOVES.append((label, p))
            MOVES_BY_LABEL[label] = p


def apply_perm(state, perm):
    return tuple(perm[s] for s in state)


def piece_faces(state):
    return [SLOT_FACE[state[j]] for j in range(24)]


def count_on_home(state, face):
    """number of pieces whose home face == face currently on that face."""
    n = 0
    for j in range(24):
        if SLOT_FACE[j] == face and SLOT_FACE[state[j]] == face:
            n += 1
    return n


def face_counts(state):
    return Counter(piece_faces(state))


def print_move_cycles(label, perm):
    seen = set()
    cyc = []
    for s in range(24):
        if s in seen:
            continue
        c = []
        cur = s
        while cur not in seen:
            seen.add(cur)
            c.append(cur)
            cur = perm[cur]
        if len(c) > 1:
            cyc.append(c)
    detail = []
    for c in cyc:
        faces_in = [SLOT_FACE[s] for s in c]
        detail.append(f"{faces_in}")
    print(f"  {label:4s} cycles={cyc and [len(c) for c in cyc]}  {detail}")


def find_sequence(start, goal_test, max_depth=9, node_cap=3_000_000):
    if goal_test(start):
        return []
    parent = {start: (None, None)}
    levels = [start]
    count = 1
    depth = 0
    while levels and depth < max_depth and count < node_cap:
        depth += 1
        nxt = []
        for st in levels:
            for label, perm in MOVES:
                ns = apply_perm(st, perm)
                if ns not in parent:
                    parent[ns] = (st, label)
                    count += 1
                    nxt.append(ns)
                    if goal_test(ns):
                        seq = []
                        node = ns
                        while parent[node][0] is not None:
                            node, lab = parent[node]
                            seq.append(lab)
                        seq.reverse()
                        return seq, depth, count
        levels = nxt
    return None, depth, count


def make_state(seq_labels):
    st = SOLVED
    for lab in seq_labels:
        st = apply_perm(st, MOVES_BY_LABEL[lab])
    return st


if __name__ == "__main__":
    print("=== exact slot cycles for all 24 base moves ===")
    for label, perm in MOVES:
        if label.endswith("'"):
            continue  # only CW base, CCW is inverse
        print_move_cycles(label, perm)

    print("\n=== construct start states (U-face focus) ===")
    # Build a few interesting scrambled states and report U/D/F counts.
    # NOTE: wide moves use lowercase labels ("f" == Fw, "r" == Rw, "u" == Uw ...).
    test_seqs = [
        ["r"],
        ["r", "F"],
        ["r", "U"],
        ["r", "U", "r'"],
        ["r", "f", "r'"],
        ["r", "F", "U", "F", "U"],
        ["r", "r", "U", "F"],
    ]
    for ts in test_seqs:
        st = make_state(ts)
        fc = face_counts(st)
        u_home = count_on_home(st, "U")
        d_home = count_on_home(st, "D")
        print(f"  seq={' '.join(ts):20s}  on-U={u_home}  on-D={d_home}  counts={dict(fc)}")

    print("\n=== BFS: fix U face (get all 4 U on U) from selected states ===")
    u_pieces = [j for j in range(24) if SLOT_FACE[j] == "U"]

    def goal_u4(state):
        return all(SLOT_FACE[state[j]] == "U" for j in u_pieces)

    for ts in test_seqs:
        st = make_state(ts)
        if goal_u4(st):
            print(f"  seq={' '.join(ts):20s}  already U-solved")
            continue
        res, d, cnt = find_sequence(st, goal_u4, max_depth=9)
        if res is None:
            print(f"  seq={' '.join(ts):20s}  NO U4 solution within depth {d} (nodes {cnt})")
        else:
            print(f"  seq={' '.join(ts):20s}  ->  {res}   (depth {d}, nodes {cnt})")
