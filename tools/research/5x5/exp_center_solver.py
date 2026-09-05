import sys, random, time
sys.path.insert(0, r"D:\coco\cube-solver")
from cube.cube5 import Cube5
from solver.center5.orbits import CenterOrbitKind, kind_of_position
from solver.center5.primitives import CENTER_INDEX, CORNER_MAIN, EDGE_MAIN
from solver.center5.conjugation import conjugate_cycle

ORBIT_IDS = {
    CenterOrbitKind.CORNER: [0, 2, 6, 8, 9, 11, 12, 13, 16, 17, 18, 20, 33, 35, 36, 37, 40, 41, 42, 44, 45, 47, 51, 53],
    CenterOrbitKind.EDGE: [1, 3, 5, 7, 10, 14, 15, 19, 21, 23, 24, 25, 28, 29, 30, 32, 34, 38, 39, 43, 46, 48, 50, 52],
}
DENSE = {k: {idx: i for i, idx in enumerate(ids)} for k, ids in ORBIT_IDS.items()}


def pos_home(c, orbit):
    dense = DENSE[orbit]
    r = {}
    for p, x in c.cubies.items():
        if len(x.stickers) == 1 and kind_of_position(x.home) == orbit:
            r[dense[CENTER_INDEX[p]]] = dense[CENTER_INDEX[x.home]]
    return r


def parity(sh):
    n = 24
    perm = [sh[i] for i in range(n)]
    seen = [False]*n; s = 0
    for i in range(n):
        if seen[i]: continue
        j = i; ln = 0
        while not seen[j]:
            seen[j] = True; j = perm[j]; ln += 1
        s += ln - 1
    return s % 2


def cycles_fn(perm_fn):
    n = 24
    cur = [perm_fn[i] for i in range(n)]
    seen = [False]*n; cycs = []
    for i in range(n):
        if seen[i]: continue
        cy = []; j = i
        while not seen[j]:
            seen[j] = True; cy.append(j); j = cur[j]
        if len(cy) > 1: cycs.append(cy)
    return cycs


def choose_B(Pc, Pe):
    if (Pc, Pe) == (0, 0): return []
    if (Pc, Pe) == (1, 0): return ["2R"]
    if (Pc, Pe) == (1, 1): return ["R"]
    return ["2R", "R"]


def solve_orbit(w, orbit, prim):
    ids = ORBIT_IDS[orbit]
    sol = []
    steps = 0
    while True:
        sh = pos_home(w, orbit)
        if all(p == h for p, h in sh.items()):
            break
        steps += 1
        if steps > 200:
            raise RuntimeError("loop")
        cycs = [cy for cy in cycles_fn(sh)]
        big = [cy for cy in cycs if len(cy) >= 3]
        if big:
            cy = big[0]
            a, b, c = cy[0], cy[1], cy[2]
            seq = conjugate_cycle(prim, (ids[a], ids[b], ids[c]))
        else:
            twos = [cy for cy in cycs if len(cy) == 2]
            if len(twos) < 2:
                raise RuntimeError("odd leftover")
            (a, b), (c, d) = twos[0], twos[1]
            seq = (conjugate_cycle(prim, (ids[a], ids[b], ids[c]))
                   + conjugate_cycle(prim, (ids[a], ids[d], ids[c])))
        w.apply_moves(seq); sol.extend(seq)
    return sol


def solve_centers(c):
    w = c.clone()
    Pc = parity(pos_home(c, CenterOrbitKind.CORNER))
    Pe = parity(pos_home(c, CenterOrbitKind.EDGE))
    B = choose_B(Pc, Pe)
    w.apply_moves(B)
    sol = list(B)
    sol += solve_orbit(w, CenterOrbitKind.CORNER, CORNER_MAIN)
    sol += solve_orbit(w, CenterOrbitKind.EDGE, EDGE_MAIN)
    return w, sol


rng = random.Random(2024)
el = ["R", "R'", "R2", "L", "L'", "U", "U'", "U2", "D", "D'", "F", "F'", "F2", "B", "B'",
      "2R", "2U", "2F", "2L", "2D", "2B"]
ok = 0; total = 0; t0 = time.time()
for trial in range(20):
    c = Cube5.solved()
    c.apply_moves([rng.choice(el) for _ in range(rng.choice([5, 10, 15, 25]))])
    total += 1
    w, sol = solve_centers(c)
    good = all(p == x.home for p, x in w.cubies.items() if len(x.stickers) == 1)
    if good:
        ok += 1
    else:
        print("FAIL", trial, "len", len(sol))
print(f"pass {ok}/{total}  avg_time {round((time.time()-t0)/total,2)}s")
