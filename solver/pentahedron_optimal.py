"""Optimal solvers for the low-order triangular prism (pentahedron).

The two- and three-order prisms have group orders 259,200 and 9,331,200. Both
factor as a product of independent piece-orbit groups (n=3 loses exactly one
parity half), so every state can be addressed by a small mixed-radix index over
the orbit coordinates. A full breadth-first table then gives God's-algorithm
distances; higher orders are far too large and keep the stabilizer-chain solver.
"""
from collections import deque
from functools import lru_cache
import zlib
from pathlib import Path

from cube.polyhedral import Move, PolyhedralPuzzle
from solver.polyhedral import identify, piece_orbits

_DATA_DIR = Path(__file__).parent / 'data'
_SUPPORTED = (2, 3)


def generators(n):
    cube = PolyhedralPuzzle('pentahedron', n)
    g = cube.geometry
    order = g.spec.turn_order
    seen = set()
    result = []
    for move in cube.moves():
        for m in (move, move.inverse(order)):
            key = (m.axis, m.layer, m.amount % order)
            if key not in seen:
                seen.add(key)
                result.append(Move(m.axis, m.layer, m.amount % order))
    return cube, g, tuple(result)


@lru_cache(maxsize=2)
def structure(n):
    """Return (generators, orbits) where each orbit is
    (points, order, transitions[move][coord], coord_of_config)."""
    _, g, gens = generators(n)
    perms = [g.permutation(m) for m in gens]
    orbits = []
    for orbit in piece_orbits('pentahedron', n):
        if len(orbit) <= 1:
            continue
        points = tuple(s for p in orbit for s in g.pieces[p])
        start = points
        coord = {start: 0}
        configs = [start]
        queue = deque([start])
        while queue:
            config = queue.popleft()
            for perm in perms:
                nxt = tuple(perm[v] for v in config)
                if nxt not in coord:
                    coord[nxt] = len(configs)
                    configs.append(nxt)
                    queue.append(nxt)
        transitions = [tuple(coord[tuple(perm[v] for v in config)] for config in configs)
                       for perm in perms]
        orbits.append((points, len(configs), transitions, coord))
    return gens, tuple(orbits)


def _weights(orbits):
    weights = [1] * len(orbits)
    for j in range(len(orbits) - 2, -1, -1):
        weights[j] = weights[j + 1] * orbits[j + 1][1]
    return weights


def _flat(orbits, weights, coords):
    total = 0
    for j, c in enumerate(coords):
        total += c * weights[j]
    return total


def _coords_of_state(orbits, state):
    coords = []
    for points, order, _trans, coord in orbits:
        config = tuple(state[s] for s in points)
        coords.append(coord[config])
    return coords


@lru_cache(maxsize=2)
def _table(n):
    return zlib.decompress((_DATA_DIR / f'pentahedron_{n}.bin').read_bytes())


def solve_pentahedron(cube, cancel=None, progress=None):
    n = cube.n
    if n not in _SUPPORTED:
        raise ValueError('No full table for this order')
    gens, orbits = structure(n)
    weights = _weights(orbits)
    table = _table(n)
    state = identify(cube)
    coords = _coords_of_state(orbits, state)
    flat = _flat(orbits, weights, coords)
    dist = table[flat]
    if dist == 255:
        raise ValueError('The entered puzzle is not a legal state')
    solution = []
    while dist:
        if cancel and cancel():
            raise InterruptedError()
        for mi, _move in enumerate(gens):
            nxt = [orbits[j][2][mi][coords[j]] for j in range(len(orbits))]
            nflat = _flat(orbits, weights, nxt)
            if table[nflat] == dist - 1:
                solution.append(gens[mi])
                coords = nxt
                flat = nflat
                dist -= 1
                break
        else:
            raise ValueError('Pentahedron table descent failed')
    if progress:
        progress(1, 1)
    from solver.polyhedral import simplify
    solution = simplify(solution, cube.geometry.spec.turn_order)
    replay = cube.entered()
    for move in solution:
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError('Pentahedron solution did not restore the puzzle')
    return solution
