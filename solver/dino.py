"""Optimal Dino Cube (order 2) solver: IDA* with two six-piece pattern databases.

The Dino Cube's twelve edges move in three-cycles, so a dedicated iterative
deepening search with admissible heuristics reaches the ten-move optimum far
below the generic three-cycle reduction. The pattern databases are generated
offline by scripts/build_dino_pdb.py and shipped in solver/data/dino_pdb.bin.
"""
from collections import deque
from functools import lru_cache
import zlib
from pathlib import Path

from cube.polyhedral import Move
from solver.polyhedral import piece_orbits, identify

_N = 12
_K = 6
_SUBSETS = (tuple(range(6)), tuple(range(6, 12)))
_PDB_PATH = Path(__file__).parent / "data" / "dino_pdb.bin"


def _rank(pos, n=_N, k=_K):
    avail = list(range(n))
    result = 0
    for i in range(k):
        j = avail.index(pos[i])
        result = result * (n - i) + j
        avail.pop(j)
    return result


def _size(n=_N, k=_K):
    result = 1
    for i in range(k):
        result *= (n - i)
    return result


@lru_cache(maxsize=1)
def _pdb():
    blob = zlib.decompress(_PDB_PATH.read_bytes())
    size = _size()
    return (blob[:size], blob[size:2 * size])


def _moves(cube):
    g = cube.geometry
    order = g.spec.turn_order
    moves = [Move(axis, layer, amount)
             for axis in range(len(g.layers))
             for layer in range(len(g.layers[axis]))
             for amount in range(1, order)]
    return moves, order


def _destinations(cube, orbit, moves):
    g = cube.geometry
    idx = {p: i for i, p in enumerate(orbit)}
    return [tuple(idx[g.stickers[g.permutation(m)[g.pieces[orbit[i]][0]]].piece]
                  for i in range(len(orbit))) for m in moves]


def _state(cube, orbit):
    g = cube.geometry
    idx = {p: i for i, p in enumerate(orbit)}
    labeled = identify(cube)
    arr = [0] * len(orbit)
    for i in range(len(orbit)):
        position = g.stickers[labeled[g.pieces[orbit[i]][0]]].piece
        arr[idx[position]] = i
    return tuple(arr)


def solve_dino(cube, cancel_event=None, progress=None):
    """Return an optimal-move word (tuple of Move) or raise on failure."""
    orbit = piece_orbits("dino", cube.n)[0]
    moves, order = _moves(cube)
    dests = _destinations(cube, orbit, moves)
    n = len(orbit)
    goal = tuple(range(n))
    if n != _N or cube.n != 2:
        raise ValueError("Dino solver supports order 2 only")

    inverse = {}
    for i, m in enumerate(moves):
        inverse[i] = next(j for j, m2 in enumerate(moves) if m2 == m.inverse(order))

    def apply(arr, dest):
        out = [0] * n
        for i in range(n):
            out[dest[i]] = arr[i]
        return tuple(out)

    pdb_a, pdb_b = _pdb()

    def heuristic(arr):
        pos = [0] * n
        for i in range(n):
            pos[arr[i]] = i
        a = pdb_a[_rank(tuple(pos[s] for s in _SUBSETS[0]))]
        b = pdb_b[_rank(tuple(pos[s] for s in _SUBSETS[1]))]
        return a if a > b else b

    start = _state(cube, orbit)
    if start == goal:
        return ()

    # The shared polyhedral solver passes a zero-argument cancellation check;
    # retain compatibility with callers that pass a threading.Event directly.
    cancelled = (cancel_event if callable(cancel_event) else
                 (lambda: cancel_event is not None and cancel_event.is_set()))
    path = []
    counter = [0]

    def search(arr, depth, bound, last):
        counter[0] += 1
        if counter[0] % 2048 == 0 and cancelled():
            raise InterruptedError()
        h = heuristic(arr)
        f = depth + h
        if f > bound:
            return f
        if arr == goal:
            return -1
        minimum = 1 << 30
        inv_last = inverse.get(last)
        for mi, dest in enumerate(dests):
            if mi == inv_last:
                continue
            path.append(mi)
            t = search(apply(arr, dest), depth + 1, bound, mi)
            if t == -1:
                return -1
            if t < minimum:
                minimum = t
            path.pop()
        return minimum

    bound = heuristic(start)
    while bound <= 40:
        t = search(start, 0, bound, None)
        if t == -1:
            break
        if t >= (1 << 30):
            raise ValueError("Dino state is not solvable")
        bound = t
    else:
        raise ValueError("Dino search exceeded the depth limit")

    word = tuple(moves[mi] for mi in path)
    replay = cube.entered()
    for move in word:
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError("Dino solution replay failed")
    return word
