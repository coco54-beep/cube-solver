"""Core-injection refinement for the high-order triangular prisms.

Every order-4/5 prism contains an n=2 analogue: the two "layer-0" piece orbits
(720x360 = 259200 states) are moved only by layer-0 turns, so they form an
independent sub-puzzle identical in size to the order-2 prism. Solving that core
optimally and re-solving the rest gives the stabiliser chain a much better
starting point than the entered state.
"""
from collections import deque
from functools import lru_cache

from cube.polyhedral import Move, PolyhedralPuzzle
from solver.polyhedral import identify, piece_orbits, simplify


def _dedup(moves, order):
    seen = set()
    out = []
    for m in moves:
        key = (m.axis, m.layer, m.amount % order)
        if key not in seen:
            seen.add(key)
            out.append(Move(m.axis, m.layer, m.amount % order))
    return out


@lru_cache(maxsize=2)
def _core(n):
    cube = PolyhedralPuzzle('pentahedron', n)
    g = cube.geometry
    order = g.spec.turn_order
    orbs = piece_orbits('pentahedron', n)
    moved = set()
    for m in cube.moves():
        if m.layer == 0:
            continue
        perm = g.permutation(m)
        for i in range(len(g.stickers)):
            if perm[i] != i:
                moved.add(i)
    core_orbits = [o for o in orbs
                   if len(o) > 1 and all(s not in moved for p in o for s in g.pieces[p])]
    gens = _dedup([m for m in cube.moves() if m.layer == 0]
                  + [m.inverse(order) for m in cube.moves() if m.layer == 0], order)
    perms = [g.permutation(m) for m in gens]
    data = []
    for o in core_orbits:
        points = tuple(s for p in o for s in g.pieces[p])
        start = points
        coord = {start: 0}
        configs = [start]
        q = deque([start])
        while q:
            c = q.popleft()
            for perm in perms:
                nx = tuple(perm[v] for v in c)
                if nx not in coord:
                    coord[nx] = len(configs)
                    configs.append(nx)
                    q.append(nx)
        trans = [tuple(coord[tuple(perm[v] for v in c)] for c in configs) for perm in perms]
        data.append((points, len(configs), trans, coord))
    weights = [1] * len(data)
    for j in range(len(data) - 2, -1, -1):
        weights[j] = weights[j + 1] * data[j + 1][1]
    size = 1
    for _p, o, _t, _c in data:
        size *= o
    dist = bytearray([255]) * size
    dist[0] = 0
    q = deque([0])
    while q:
        r = q.popleft()
        coords = [(r // weights[j]) % data[j][1] for j in range(len(data))]
        for mi in range(len(gens)):
            nr = 0
            for j in range(len(data)):
                nr += data[j][2][mi][coords[j]] * weights[j]
            if dist[nr] == 255:
                dist[nr] = dist[r] + 1
                q.append(nr)
    return cube, g, order, gens, data, weights, dist


def _solve_core(n, state):
    cube, g, order, gens, data, weights, dist = _core(n)
    coords = [data[j][3][tuple(state[s] for s in data[j][0])] for j in range(len(data))]
    flat = sum(coords[j] * weights[j] for j in range(len(data)))
    moves = []
    d = dist[flat]
    while d:
        for mi in range(len(gens)):
            nxt = [data[j][2][mi][coords[j]] for j in range(len(data))]
            nf = sum(nxt[j] * weights[j] for j in range(len(data)))
            if dist[nf] == d - 1:
                moves.append(gens[mi])
                coords = nxt
                flat = nf
                d -= 1
                break
        else:
            return None
    return moves


def core_injection(cube,cancel=None):
    """Return a verified solution that first solves the n=2 core, or None."""
    from solver.drum_prism import solve_drum_prism

    if cube.n not in (4, 5):
        return None
    if cancel and cancel():
        raise InterruptedError()
    state = identify(cube)
    core_moves = _solve_core(cube.n, state)
    if cancel and cancel():
        raise InterruptedError()
    if core_moves is None:
        return None
    work = cube.clone()
    for move in core_moves:
        work.apply_move(move)
    try:
        rest = solve_drum_prism(work,cancel)
    except InterruptedError:
        raise
    except Exception:
        return None
    return simplify(tuple(core_moves) + tuple(rest), cube.geometry.spec.turn_order)
