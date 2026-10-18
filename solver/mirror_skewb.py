"""Complete Mirror Skewb solver: IDA* over the coloured Skewb plus centre twists.

The coloured Skewb pattern databases alone do not describe a mirror centre's
visible direction.  This module adds the six centre twists to the search state
and uses an exact breadth-first table over the centre permutation/twist system
as a second admissible heuristic.  The result is a short complete word instead
of a long stabiliser-chain walk.
"""
import math
from array import array
from collections import deque
from functools import lru_cache

from cube.mastermorphix import IDENTITY
from cube.polyhedral import PolyhedralPuzzle, rotate
from cube.mirror_tower import frame_key, multiply
from cube.mirror_pyraminx import placements
from solver.skewb import _model
from solver.polyhedral import identify
from solver.mirror_pyraminx import solve_oriented_mirror

_N = 30


@lru_cache(maxsize=1)
def _mirror_model():
    (moves, order, dest, full, loc, a_idx, b_idx, c_idx,
     rank_a, rank_b, rank_c, table_a, table_b) = _model()
    g = PolyhedralPuzzle.solved('skewb', 3).geometry
    homes = [g.stickers[full[24 + j]].piece for j in range(6)]
    hidx = {h: j for j, h in enumerate(homes)}
    positions = list(homes)

    # Sticker permutations as 256-byte translate tables (values stay under 30).
    sticker_trans = [bytes(d[v] if v < _N else v for v in range(256)) for d in dest]

    turns = [tuple(rotate(v, g.spec.axes[m.axis], 2 * math.pi * m.amount / 3)
                   for v in IDENTITY) for m in moves]
    slot_dest = [[dest[m][24 + j] - 24 for j in range(6)] for m in range(len(moves))]
    keys = {(h, j): [frame_key(f) for f in placements(3, h, positions[j], 'skewb')]
            for h in homes for j in range(6)}

    def next_bit(m, h, j, b):
        if slot_dest[m][j] == j:
            return b
        frame = placements(3, h, positions[j], 'skewb')[b]
        return keys[(h, slot_dest[m][j])].index(frame_key(multiply(turns[m], frame)))

    twist = [[[[next_bit(m, h, j, b) for b in range(2)] for j in range(6)]
              for h in homes] for m in range(len(moves))]

    perms = []

    def build(prefix, remaining):
        if not remaining:
            perms.append(tuple(prefix))
            return
        for value in remaining:
            build(prefix + [value], [x for x in remaining if x != value])

    build([], list(range(6)))
    rank_of = {perm: i for i, perm in enumerate(perms)}

    # Exact distances for the six-centre subsystem (permutation x twist bits).
    dist = bytearray([255]) * (720 * 64)
    dist[0] = 0
    queue = deque([(tuple(range(6)), 0)])
    while queue:
        perm, mask = queue.popleft()
        depth = dist[rank_of[perm] * 64 + mask]
        for m in range(len(moves)):
            nperm = [0] * 6
            nmask = 0
            for j in range(6):
                hi = perm[j]
                b = (mask >> hi) & 1
                nperm[slot_dest[m][j]] = hi
                if twist[m][hi][j][b]:
                    nmask |= 1 << hi
            key = rank_of[tuple(nperm)] * 64 + nmask
            if dist[key] == 255:
                dist[key] = depth + 1
                queue.append((tuple(nperm), nmask))

    # Flattened centre-state transitions so the search avoids re-ranking.
    centre_next = []
    for m in range(len(moves)):
        row = array('H', [0]) * (720 * 64)
        for rank, perm in enumerate(perms):
            for mask in range(64):
                nperm = [0] * 6
                nmask = 0
                for j in range(6):
                    hi = perm[j]
                    b = (mask >> hi) & 1
                    nperm[slot_dest[m][j]] = hi
                    if twist[m][hi][j][b]:
                        nmask |= 1 << hi
                row[rank * 64 + mask] = rank_of[tuple(nperm)] * 64 + nmask
        centre_next.append(row)

    rank_a_b = {bytes(k): v for k, v in rank_a.items()}
    rank_b_b = {bytes(k): v for k, v in rank_b.items()}
    rank_c_b = {bytes(k): v for k, v in rank_c.items()}
    return (moves, order, full, loc, sticker_trans, rank_a_b, rank_b_b, rank_c_b,
            table_a, table_b, dist, centre_next,
            bytes((v - 12) & 255 for v in range(256)),
            bytes((v - 24) & 255 for v in range(256)), rank_of, homes, hidx)


def _centre_state(cube, homes, hidx, rank_of):
    g = cube.geometry
    bits = [0] * 6
    perm = [0] * 6
    for position, piece in cube.pieces.items():
        if len(g.pieces[position]) != 1:
            continue
        h = piece.home
        hi = hidx[h]
        j = homes.index(position)
        perm[j] = hi
        keys = [frame_key(f) for f in placements(3, h, homes[j], 'skewb')]
        bits[hi] = keys.index(frame_key(piece.frame))
    mask = 0
    for hi in range(6):
        if bits[hi]:
            mask |= 1 << hi
    return rank_of[tuple(perm)] * 64 + mask


def solve_mirror_skewb(cube, cancel=None, progress=None):
    if cube.is_solved():
        return ()
    # The ordinary solve is cheap and already finishes most mirror scrambles.
    from solver.polyhedral import solve_polyhedral
    prefix = tuple(solve_polyhedral(cube.ordinary_state(), cancel, progress))
    residual = cube.clone()
    for move in prefix:
        if cancel and cancel():
            raise InterruptedError()
        residual.apply_move(move)
    if residual.is_solved():
        return prefix
    try:
        return _solve_complete(cube, cancel)
    except (ValueError, KeyError, IndexError):
        return solve_oriented_mirror(cube, cancel, progress)


def _solve_complete(cube, cancel=None):
    (moves, order, full, loc, sticker_trans, rank_a, rank_b, rank_c,
     table_a, table_b, dist, centre_next, sub12, sub24, rank_of,
     homes, hidx) = _mirror_model()
    labelled = identify(cube.ordinary_state())
    start = bytes(loc[labelled[s]] for s in full)
    centre = _centre_state(cube, homes, hidx, rank_of)
    goal = bytes(range(_N))
    if start == goal and centre == 0:
        return ()
    inverse = {}
    for i, move in enumerate(moves):
        inverse[i] = next(j for j, other in enumerate(moves)
                          if other == move.inverse(order))
    path = []
    nodes = [0]

    def heuristic(stickers, state):
        a = stickers[:12]
        b = stickers[12:24].translate(sub12)
        c = stickers[24:].translate(sub24)
        rc = rank_c[c]
        ha = table_a[rank_a[a] * 360 + rc]
        hb = table_b[rank_b[b] * 360 + rc]
        h = ha if ha > hb else hb
        hc = dist[state]
        return h if h > hc else hc

    def search(stickers, state, depth, bound, last_axis):
        nodes[0] += 1
        if nodes[0] & 4095 == 0 and cancel and cancel():
            raise InterruptedError()
        h = heuristic(stickers, state)
        if depth + h > bound:
            return depth + h
        if state == 0 and stickers == goal:
            return -1
        key = (stickers, state)
        seen = table.get(key)
        if seen is not None and seen <= depth:
            return bound + 1
        table[key] = depth
        minimum = 1 << 30
        children = []
        for mi in range(len(moves)):
            if moves[mi].axis == last_axis:
                continue
            nxt = stickers.translate(sticker_trans[mi])
            nstate = centre_next[mi][state]
            children.append((heuristic(nxt, nstate), mi, nxt, nstate))
        children.sort()
        for _, mi, nxt, nstate in children:
            path.append(mi)
            result = search(nxt, nstate, depth + 1, bound, moves[mi].axis)
            if result == -1:
                return -1
            if result < minimum:
                minimum = result
            path.pop()
        return minimum

    bound = heuristic(start, centre)
    while bound <= 40:
        if cancel and cancel():
            raise InterruptedError()
        table = {}
        result = search(start, centre, 0, bound, -1)
        if result == -1:
            break
        if result >= (1 << 30):
            raise ValueError('Mirror Skewb state is not solvable')
        bound = result
    else:
        raise ValueError('Mirror Skewb search exceeded the depth limit')

    word = tuple(moves[mi] for mi in path)
    replay = cube.clone()
    for move in word:
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError('Mirror Skewb solution replay failed')
    return word
