"""Probe: verify the 3-phase 4x4 center approach end-to-end on random scrambles.

Phase 2: D-home centers -> 4 D-slots, all 24 moves.
Phase 3: U-home centers -> 4 U-slots, D-preserving moves.
Phase 4: 16 side centers (face-labeled), 12 UD-preserving moves (p4_table.bin).
"""
import os
import random
import struct
import time
import itertools
from collections import deque

from primitives import MOVES, SLOT_FACE, CENTER_HOMES, SLOT_INDEX, FACES
from cube.cube4 import Cube4

SIDE_FACES = ["F", "B", "R", "L"]
FACE_SLOTS = {f: [i for i in range(24) if SLOT_FACE[i] == f] for f in FACES}
SIDE_ORDER = [s for s in range(24) if SLOT_FACE[s] in SIDE_FACES]
side_index = {s: i for i, s in enumerate(SIDE_ORDER)}


def inv_perm(p):
    inv = [0] * len(p)
    for i, v in enumerate(p):
        inv[v] = i
    return inv


ITEMS = [(lab, p, inv_perm(p)) for lab, p in MOVES.items()]
LABELS = [it[0] for it in ITEMS]


def d_preserving(items):
    slots = FACE_SLOTS["D"]
    return [it for it in items if all(it[1][s] in slots for s in slots)]


def ud_preserving(items):
    us = FACE_SLOTS["U"]
    ds = FACE_SLOTS["D"]
    return [it for it in items if all(it[1][s] in us for s in us)
            and all(it[1][s] in ds for s in ds)]


def bfs_goals(goal_set, items):
    dist = {g: 0 for g in goal_set}
    parent = {}
    q = deque(list(goal_set))
    while q:
        s = q.popleft()
        for mi, (lab, p, ip) in enumerate(items):
            sp = tuple(ip[x] for x in s)
            if sp not in dist:
                dist[sp] = dist[s] + 1
                parent[sp] = mi
                q.append(sp)
    return dist, parent


def extract_face_state(cube, face):
    homes = CENTER_HOMES[face]
    h2c = {c.home: c for c in cube.cubies.values() if len(c.stickers) == 1}
    return tuple(SLOT_INDEX[h2c[h].pos] for h in homes)


def solve_with_policy(state, dist, parent, goal_set, items):
    seq = []
    cur = state
    while cur not in goal_set:
        if cur not in parent:
            return None
        mi = parent[cur]
        seq.append(items[mi][0])
        p = items[mi][1]
        cur = tuple(p[x] for x in cur)
    return seq


# ------------------------------------------------------------------ Phase 2
D_GOAL = set(itertools.permutations(FACE_SLOTS["D"]))
print("Building Phase 2 (D, all 24) ...", flush=True)
t0 = time.time()
d2_dist, d2_parent = bfs_goals(D_GOAL, ITEMS)
print(f"  orbit={len(d2_dist)} maxdist={max(d2_dist.values())} "
      f"t={time.time()-t0:.2f}s")

# ------------------------------------------------------------------ Phase 3
DPRES = d_preserving(ITEMS)
print(f"D-preserving moves ({len(DPRES)}): {[it[0] for it in DPRES]}")
U_GOAL = set(itertools.permutations(FACE_SLOTS["U"]))
print("Building Phase 3 (U, D-preserving) ...", flush=True)
t0 = time.time()
u3_dist, u3_parent = bfs_goals(U_GOAL, DPRES)
nond = [i for i in range(24) if SLOT_FACE[i] != "D"]
allnond = sum(1 for s in u3_dist if all(t in nond for t in s))
print(f"  orbit={len(u3_dist)} maxdist={max(u3_dist.values())} "
      f"nonD-only={allnond} t={time.time()-t0:.2f}s")

# ------------------------------------------------------------------ Phase 4
print("Loading p4_table.bin ...", flush=True)
SIDE_MOVES = []
for lab, p in MOVES.items():
    if not (all(p[s] in FACE_SLOTS["U"] for s in FACE_SLOTS["U"])
            and all(p[s] in FACE_SLOTS["D"] for s in FACE_SLOTS["D"])):
        continue
    sp = []
    ok = True
    for s in SIDE_ORDER:
        d = p[s]
        if SLOT_FACE[d] not in SIDE_FACES:
            ok = False
            break
        sp.append(side_index[d])
    if ok and tuple(sp) != tuple(range(16)):
        SIDE_MOVES.append((lab, tuple(sp)))

SIDE_LABELS = [m[0] for m in SIDE_MOVES]
print(f"Phase4 side moves ({len(SIDE_MOVES)}): {SIDE_LABELS}")


def face_code(cube):
    h2c = {}
    for c in cube.cubies.values():
        if len(c.stickers) == 1:
            h2c[c.home] = c
    out = 0
    for i, s in enumerate(SIDE_ORDER):
        cub = cube.cubies.get(SLOT_POS[s])
        assert cub is not None
        hf = SLOT_FACE[SLOT_INDEX[cub.home]]
        assert hf in SIDE_FACES, f"center {cub.home} face {hf} at side slot"
        v = 0 if hf == "F" else 1 if hf == "B" else 2 if hf == "R" else 3
        out |= v << (2 * i)
    return out


SLOT_POS = [None] * 24
for idx, p in enumerate(ALL_CENTERS := [h for f in ("U", "D", "F", "B", "R", "L")
                                     for h in CENTER_HOMES[f]]):
    SLOT_POS[idx] = p

IDENT_STATE = tuple(
    0 if SLOT_FACE[s] == "F" else
    1 if SLOT_FACE[s] == "B" else
    2 if SLOT_FACE[s] == "R" else
    3 for s in SIDE_ORDER)
IDENT_CODE = 0
for i in range(16):
    IDENT_CODE |= IDENT_STATE[i] << (2 * i)

P4 = os.path.join(os.path.dirname(__file__), "p4_table.bin")
p4_table = {}
with open(P4, "rb") as f:
    hdr = f.read(4)
    assert hdr == b"C4PT", hdr
    cnt = struct.unpack("<I", f.read(4))[0]
    for _ in range(cnt):
        code, par = struct.unpack("<IB", f.read(5))
        p4_table[code] = par
print(f"  p4 entries={len(p4_table)}")


def solve_p4(code):
    seq = []
    cur = code
    while cur != IDENT_CODE:
        par = p4_table[cur]
        seq.append(SIDE_LABELS[par])
        sp = SIDE_MOVES[par][1]
        inv = inv_perm(sp)
        # predecessor: applying sp to pred gives cur  -> pred = ?
        # cur = apply(sp, pred): cur[sp[i]] = pred[i]  -> pred[sp[i]] = cur[i]
        pred = [0] * 16
        for i in range(16):
            pred[sp[i]] = (cur >> (2 * i)) & 3
        cur = 0
        for i in range(16):
            cur |= pred[i] << (2 * i)
    return seq


def apply_moves(cube, seq):
    for m in seq:
        cube.apply_move(m)


def centers_on_faces(cube):
    h2c = {c.home: c for c in cube.cubies.values() if len(c.stickers) == 1}
    bad = 0
    for h, c in h2c.items():
        hf = SLOT_FACE[SLOT_INDEX[h]]
        pf = SLOT_FACE[SLOT_INDEX[c.pos]]
        if hf != pf:
            bad += 1
    return bad


print("\n=== End-to-end on random scrambles ===")
random.seed(1234)
succ = 0
for trial in range(10):
    cube = Cube4.solved()
    for _ in range(30):
        cube.apply_move(random.choice(LABELS))
    work = cube.clone()
    total = 0
    ok = True

    st = extract_face_state(work, "D")
    seq2 = solve_with_policy(st, d2_dist, d2_parent, D_GOAL, ITEMS)
    if seq2 is None:
        ok = False
    else:
        apply_moves(work, seq2)
        total += len(seq2)
        if extract_face_state(work, "D") not in D_GOAL:
            ok = False

    st = extract_face_state(work, "U")
    seq3 = solve_with_policy(st, u3_dist, u3_parent, U_GOAL, DPRES)
    if seq3 is None:
        ok = False
    else:
        apply_moves(work, seq3)
        total += len(seq3)
        if extract_face_state(work, "U") not in U_GOAL:
            ok = False

    code = face_code(work)
    seq4 = solve_p4(code)
    apply_moves(work, seq4)
    total += len(seq4)
    bad = centers_on_faces(work)
    if bad != 0:
        ok = False

    if ok:
        succ += 1
    print(f"  trial {trial}: ok={ok} moves={total} bad_centers={bad}")

print(f"\nSUCCESS: {succ}/10")
