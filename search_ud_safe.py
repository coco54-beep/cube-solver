"""Find wide-turn sequences that net-preserve U/D face assignment.

These are the building blocks for finishing side centers with U/D complete
(Phase 2 of the classical 4x4 center method).

State = face-assignment: fa[i] = face-index of the piece occupying slot i.
(Quotient by same-face interchangeability -> small state space.)
U/D-safe: U/D slots hold U/D pieces; side slots (F/B/R/L) hold side pieces.
"""
import primitives as P
from collections import deque, Counter

FNAME = ["U", "D", "F", "B", "R", "L"]
FIDX = {f: i for i, f in enumerate(FNAME)}
SLOT_FIDX = [FIDX[f] for f in P.SLOT_FACE]

UD_SLOTS = [i for i in range(24) if P.SLOT_FACE[i] in ("U", "D")]
SIDE_SLOTS = [i for i in range(24) if P.SLOT_FACE[i] in ("F", "B", "R", "L")]


def apply_move(fa, mv):
    p = P.MOVES[mv]
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


def side_progress(fa):
    """Number of side slots holding a piece of the same face."""
    return sum(1 for i in SIDE_SLOTS if fa[i] == SLOT_FIDX[i])


GENS = P.WIDE + [w + "'" for w in P.WIDE]

start = tuple(SLOT_FIDX)
seen = {start: []}
q = deque([start])
MAXD = 6
per_depth = {0: 1}
depth = 0
while q:
    cur = q.popleft()
    seq = seen[cur]
    d = len(seq)
    if d >= MAXD:
        continue
    for mv in GENS:
        nf = apply_move(list(cur), mv)
        nft = tuple(nf)
        if nft not in seen and ud_safe(nf):
            seen[nft] = seq + [mv]
            q.append(nft)

total = len(seen)
print("total U/D-safe face-assignments reachable (depth<=%d):" % MAXD, total)

# Classify by (side_progress, cycle-length multiset of net distinct perm).
c = Counter()
examples = {}
for st, seq in seen.items():
    if not seq:
        continue
    sp = side_progress(st)
    perm = P.net_perm(seq)
    cyc = P.cycles(perm)
    cycsig = tuple(sorted(len(x) for x in cyc))
    key = (sp, cycsig)
    c[key] += 1
    if key not in examples:
        examples[key] = seq

print("\n=== (side_progress, net cycle lengths) : count ===")
for k in sorted(c):
    print("  sp=%d cycles=%s : %d" % (k[0], k[1], c[k]))

print("\n=== example sequence per class (shortest side progress first) ===")
for k, seq in sorted(examples.items(), key=lambda kv: kv[0][0]):
    print("  sp=%d cycles=%s :" % (k[0], k[1]), " ".join(seq))
