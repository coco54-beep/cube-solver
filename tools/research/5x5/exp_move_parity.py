import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from cube.cube5 import Cube5
from solver.center5.orbits import CenterOrbitKind, kind_of_position
from solver.center5.primitives import CENTER_ORDER, CENTER_INDEX


def perm_for_orbit(cube, orbit):
    cur = {}
    for p, x in cube.cubies.items():
        if len(x.stickers) == 1 and kind_of_position(x.home) == orbit:
            cur[CENTER_INDEX[p]] = CENTER_INDEX[x.home]
    return cur


def orbit_parity(cur):
    h2p = {h: p for p, h in cur.items()}
    nodes = sorted(h2p.keys())
    idx = {v: i for i, v in enumerate(nodes)}
    perm = [idx[h2p[n]] for n in nodes]
    seen = [False]*24; s=0
    for i in range(24):
        if seen[i]: continue
        j=i; ln=0
        while not seen[j]:
            seen[j]=True; j=perm[j]; ln+=1
        s += ln-1
    return s % 2


# classify each single move's parity effect on corner and edge orbits
moves = ["R","L","U","D","F","B","2R","2L","2U","2D","2F","2B"]
for mv in moves:
    c = Cube5.solved()
    c.apply_move(mv)
    cp = orbit_parity(perm_for_orbit(c, CenterOrbitKind.CORNER))
    ep = orbit_parity(perm_for_orbit(c, CenterOrbitKind.EDGE))
    print(f"{mv}: corner={cp} edge={ep}")
