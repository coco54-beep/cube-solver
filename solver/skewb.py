"""Optimal order-3 Skewb solver: IDA* with two coupled pattern databases.

The eight corners split into two four-corner orbits (A, B); the six centres
form orbit C. Two databases over (A,C) and (B,C) give a strong admissible
heuristic. Each database is a product of an orbit-A (or -B) rank and a centre
rank, so it ships as a flat 349920-byte table built by build_skewb_pdb.py.
"""
from collections import deque
from functools import lru_cache
import zlib
from pathlib import Path

from cube.polyhedral import Move, PolyhedralPuzzle
from solver.polyhedral import piece_orbits, identify

_PDB_PATH = Path(__file__).parent / "data" / "skewb_pdb.bin"


def _reachable_rank(indices, dest):
    proj = {fp: j for j, fp in enumerate(indices)}
    k = len(indices)
    sub = [tuple(proj[dest[m][indices[p]]] for p in range(k)) for m in range(len(dest))]
    start = tuple(range(k))
    seen = {start}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for d in sub:
            nxt = tuple(d[v] for v in state)
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return {cfg: i for i, cfg in enumerate(sorted(seen))}


@lru_cache(maxsize=1)
def _model():
    cube = PolyhedralPuzzle.solved("skewb", 3)
    g = cube.geometry
    order = g.spec.turn_order
    orbits = piece_orbits("skewb", 3)
    corner = tuple(s for o in orbits if len(g.pieces[o[0]]) == 3
                   for p in o for s in g.pieces[p])
    centre = tuple(s for o in orbits if len(g.pieces[o[0]]) == 1
                   for p in o for s in g.pieces[p])
    full = corner + centre
    loc = {s: i for i, s in enumerate(full)}
    moves = [Move(a, l, amt)
             for a in range(len(g.layers))
             for l in range(len(g.layers[a]))
             for amt in range(1, order)]
    dest = [tuple(loc[g.permutation(m)[s]] for s in full) for m in moves]
    n = len(full)
    a_idx = list(range(0, 12))
    b_idx = list(range(12, 24))
    c_idx = list(range(len(corner), n))
    rank_a = _reachable_rank(a_idx, dest)
    rank_b = _reachable_rank(b_idx, dest)
    rank_c = _reachable_rank(c_idx, dest)
    blob = zlib.decompress(_PDB_PATH.read_bytes())
    size = len(rank_a) * len(rank_c)
    return (moves, order, dest, full, loc, a_idx, b_idx, c_idx,
            rank_a, rank_b, rank_c, blob[:size], blob[size:2 * size])


def solve_skewb(cube, cancel_event=None, progress=None):
    if cube.n != 3:
        raise ValueError("Skewb solver supports order 3 only")
    (moves, order, dest, full, loc, a_idx, b_idx, c_idx,
     rank_a, rank_b, rank_c, table_a, table_b) = _model()
    centre_count = len(rank_c)
    n = len(full)
    goal = tuple(range(n))
    offset_c = len(a_idx) + len(b_idx)

    def heuristic(st):
        a = tuple(st[i] for i in a_idx)
        b = tuple(st[i] - 12 for i in b_idx)
        c = tuple(st[i] - offset_c for i in c_idx)
        rc = rank_c[c]
        ha = table_a[rank_a[a] * centre_count + rc]
        hb = table_b[rank_b[b] * centre_count + rc]
        return ha if ha > hb else hb

    def apply(st, d):
        return tuple(d[v] for v in st)

    labeled = identify(cube)
    start = tuple(loc[labeled[s]] for s in full)
    if start == goal:
        return ()

    # The shared polyhedral solver passes a zero-argument cancellation check;
    # retain compatibility with callers that pass a threading.Event directly.
    cancelled = (cancel_event if callable(cancel_event) else
                 (lambda: cancel_event is not None and cancel_event.is_set()))
    inverse = {}
    for i, m in enumerate(moves):
        inverse[i] = next((j for j, m2 in enumerate(moves) if m2 == m.inverse(order)), None)
    path = []

    def search(st, depth, bound, last):
        hh = heuristic(st)
        if depth + hh > bound:
            return depth + hh
        if st == goal:
            return -1
        minimum = 1 << 30
        inv_last = inverse.get(last)
        for mi, d in enumerate(dest):
            if mi == inv_last:
                continue
            path.append(mi)
            t = search(apply(st, d), depth + 1, bound, mi)
            if t == -1:
                return -1
            if t < minimum:
                minimum = t
            path.pop()
        return minimum

    bound = heuristic(start)
    while bound <= 40:
        if cancelled():
            raise InterruptedError()
        t = search(start, 0, bound, None)
        if t == -1:
            break
        if t >= (1 << 30):
            raise ValueError("Skewb state is not solvable")
        bound = t
    else:
        raise ValueError("Skewb search exceeded the depth limit")

    word = tuple(moves[mi] for mi in path)
    replay = cube.entered()
    for move in word:
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError("Skewb solution replay failed")
    return word


def solve_high_order_core(cube, cancel=None, progress=None):
    """Solve a 5/7 Skewb's corner/face-centre core with the 3x3 solver.

    Those two core orbits have the exact 3x3 piece layout. Only the outermost
    layer at each end of a high-order axis touches them, so the resulting word
    maps directly while leaving the additional middle orbits for reduction.
    """
    if cube.puzzle_kind != 'skewb' or cube.n not in (5, 7):
        raise ValueError('High-order Skewb core supports orders 5 and 7')
    high_g=cube.geometry
    low=PolyhedralPuzzle.solved('skewb',3)
    low_g=low.geometry

    def signature(g,piece):
        return tuple(sorted(g.stickers[s].face for s in g.pieces[piece]))

    def core_orbits(g,orbits):
        return tuple(orbit for orbit in orbits
                     if len(g.pieces[orbit[0]])==3 or
                     (len(orbit)==6 and len(g.pieces[orbit[0]])==1))

    high_orbits=core_orbits(high_g,piece_orbits('skewb',cube.n))
    low_orbits=core_orbits(low_g,piece_orbits('skewb',3))
    low_by_orbit={tuple(sorted(signature(low_g,p) for p in orbit)):orbit
                  for orbit in low_orbits}
    for high_orbit in high_orbits:
        orbit_key=tuple(sorted(signature(high_g,p) for p in high_orbit))
        low_orbit=low_by_orbit.get(orbit_key)
        if low_orbit is None:
            raise ValueError('High-order Skewb core does not match the 3x3 core')
        low_by_piece={signature(low_g,p):p for p in low_orbit}
        for high_piece in high_orbit:
            low_piece=low_by_piece[signature(high_g,high_piece)]
            low_by_face={low_g.stickers[s].face:s for s in low_g.pieces[low_piece]}
            for high_sticker in high_g.pieces[high_piece]:
                low_sticker=low_by_face[high_g.stickers[high_sticker].face]
                low.colors[low_sticker]=cube.colors[high_sticker]

    core_word=solve_skewb(low,cancel,progress)
    mapped=[]
    for move in core_word:
        layer=0 if move.layer==0 else len(high_g.layers[move.axis])-1
        mapped.append(Move(move.axis,layer,move.amount))
    replay=cube.entered()
    for move in mapped:
        replay.apply_move(move)
    for orbit in high_orbits:
        if any(replay.colors[s]!=high_g.stickers[s].face
               for piece in orbit for s in high_g.pieces[piece]):
            raise ValueError('Mapped 3x3 Skewb core solution did not solve the high-order core')
    return tuple(mapped)
