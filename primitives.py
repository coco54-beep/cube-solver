"""Find clean reusable primitives for the 4x4 center solver.

A "primitive" is a short move sequence whose net permutation on the 24 center
pieces has small, useful support (e.g. a 3-cycle, or two 3-cycles). We compute
net permutations of candidate sequences from the 6 wide turns and report which
are clean building blocks for a constructive sort.
"""

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
SLOT_FACE = []
for p in ALL_CENTERS:
    x, y, z = p
    if abs(x) == 3:
        SLOT_FACE.append("R" if x > 0 else "L")
    elif abs(y) == 3:
        SLOT_FACE.append("U" if y > 0 else "D")
    else:
        SLOT_FACE.append("F" if z > 0 else "B")
SLOT_FACE = list(SLOT_FACE)

FACES = ["U", "D", "F", "B", "R", "L"]
SOLVED = tuple(range(24))
WIDE = ["u", "d", "f", "b", "r", "l"]


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


MOVES = {}
for f in FACES:
    for wide in (False, True):
        for ccw in (False, True):
            label = (f.lower() if wide else f) + ("'" if ccw else "")
            MOVES[label] = base_perm(f, wide, ccw)


def compose(*perms):
    """Net perm of a sequence of perms applied in order: result = pk o ... o p1."""
    out = list(range(24))
    for perm in perms:
        out = [perm[i] for i in out]
    return out


def net_perm(seq):
    perms = [MOVES[m] for m in seq]
    return compose(*perms)


def cycles(perm):
    seen = set()
    out = []
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
            out.append(c)
    return out


def support(perm):
    return sorted(s for s in range(24) if perm[s] != s)


def describe(seq):
    perm = net_perm(seq)
    sup = support(perm)
    cyc = cycles(perm)
    face_sig = sorted(set(SLOT_FACE[s] for s in sup))
    return perm, len(sup), [len(c) for c in cyc], face_sig


if __name__ == "__main__":
    print("=== single wide turns ===")
    for w in WIDE:
        perm, sup, cyc, fsig = describe([w])
        print(f"  {w:3s} support={sup:2d} cycles={cyc} faces={fsig}")

    print("\n=== commutators [Wi, Wj] = Wi Wj Wi' Wj' ===")
    for i in WIDE:
        for j in WIDE:
            if i == j:
                continue
            seq = [i, j, i + "'", j + "'"]
            perm, sup, cyc, fsig = describe(seq)
            if sup <= 8:
                print(f"  [{i},{j}] support={sup:2d} cycles={cyc} faces={fsig}")

    print("\n=== [Wi, Wj2] = Wi Wj2 Wi' Wj2  (Wj twice) ===")
    for i in WIDE:
        for j in WIDE:
            if i == j:
                continue
            seq = [i, j, j, i + "'", j, j]
            perm, sup, cyc, fsig = describe(seq)
            if sup <= 8:
                print(f"  [{i},{j}2] support={sup:2d} cycles={cyc} faces={fsig}")
