"""Deeper U/D-safe search: do side-turn (f/b/r/l) sequences ever come back
U/D-safe, and at what depth? Prints per-depth growth + side-turn examples.
"""
from __future__ import annotations

import sys
from collections import deque

from primitives import MOVES, SLOT_FACE, WIDE

MAXD = int(sys.argv[1]) if len(sys.argv) > 1 else 11

FNAME = ["U", "D", "F", "B", "R", "L"]
FIDX = {f: i for i, f in enumerate(FNAME)}
SLOT_FIDX = [FIDX[f] for f in SLOT_FACE]
UD_SLOTS = [i for i in range(24) if SLOT_FACE[i] in ("U", "D")]
SIDE_SLOTS = [i for i in range(24) if SLOT_FACE[i] in ("F", "B", "R", "L")]


def apply_move(fa, mv):
    p = MOVES[mv]
    new = [0] * 24
    for i in range(24):
        new[p[i]] = fa[i]
    return new


def ud_safe(fa):
    for i in UD_SLOTS:
        if fa[i] != SLOT_FIDX[i]:
            return False
    for i in SIDE_SLOTS:
        if FNAME[fa[i]] in ("U", "D"):
            return False
    return True


GENS = WIDE + [w + "'" for w in WIDE]

start = tuple(SLOT_FIDX)
seen = {start: []}
q = deque([start])
growth = {0: 1}

while q:
    cur = q.popleft()
    seq = seen[cur]
    if len(seq) >= MAXD:
        continue
    for mv in GENS:
        nf = apply_move(list(cur), mv)
        nft = tuple(nf)
        if nft not in seen and ud_safe(nf):
            seen[nft] = seq + [mv]
            q.append(nft)
            nd = len(seen[nft])
            growth[nd] = growth.get(nd, 0) + 1

print("total U/D-safe (depth<=%d): %d" % (MAXD, len(seen)))
for d in sorted(growth):
    print("  depth %d : %d" % (d, growth[d]))

print("\nside-turn examples (use f/b/r/l):")
shown = 0
for st, seq in seen.items():
    if shown >= 15:
        break
    if any(mv[0] in ("f", "b", "r", "l") for mv in seq):
        print("  len=%d : %s" % (len(seq), " ".join(seq)))
        shown += 1
