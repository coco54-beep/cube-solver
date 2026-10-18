"""Dedicated Skewb Ultimate solver.

The puzzle is a Skewb mechanism whose eight corners and six centres carry
extra visible orientation.  We map its body (corner positions/orientations and
centre positions) onto an ordinary Skewb state, solve that state's pattern
databases, and add the six independent centre flips as a second coordinate.
An exact breadth-first table over (centre permutation, flip bits) supplies the
matching admissible heuristic, so one IDA* search returns a complete word of
about ten moves instead of a long stabiliser-chain walk.
"""
from array import array
from collections import deque
from functools import lru_cache
import itertools

from cube.polyhedral import Move, PolyhedralPuzzle
from solver.polyhedral import identify
from solver.skewb import _model as _skewb_model

_N = 30

# Isomorphism from the Skewb Ultimate piece/atom layout to the ordinary Skewb.
# Both mechanisms have eight 120-degree corner turns; the indices differ.
_PIECE_MAP = (4, 2, 6, 1, 7, 9, 3, 13, 0, 5, 10, 8, 12, 11)
_ATOM_MAP = (15, 14, 0, 1, 11, 10, 7, 6, 8, 9, 4, 5, 12, 13, 3, 2)


def _atoms(g):
    order = g.spec.turn_order
    return [Move(axis, layer, amount)
            for axis in range(len(g.layers))
            for layer in range(len(g.layers[axis]))
            for amount in range(1, order)]


def _piece_perm(perm, g):
    return tuple(g.stickers[perm[g.pieces[i][0]]].piece
                 for i in range(len(g.pieces)))


@lru_cache(maxsize=1)
def _maps():
    actual = PolyhedralPuzzle.solved('skewb_ultimate', 3)
    standard = PolyhedralPuzzle.solved('skewb', 3)
    ga, gs = actual.geometry, standard.geometry
    aa, sa = _atoms(ga), _atoms(gs)
    pa = [tuple(ga.permutation(m)) for m in aa]
    ps = [tuple(gs.permutation(m)) for m in sa]
    pap = [_piece_perm(p, ga) for p in pa]
    psp = [_piece_perm(p, gs) for p in ps]

    # Verify the hard-coded piece/move bijection against both mechanisms.
    for mi in range(len(aa)):
        atom = _ATOM_MAP[mi]
        for p in range(len(ga.pieces)):
            if _PIECE_MAP[pap[mi][p]] != psp[atom][_PIECE_MAP[p]]:
                raise ValueError('Skewb Ultimate body map is inconsistent')

    ca = [p for p in range(len(ga.pieces)) if len(ga.pieces[p]) == 3]
    cs = [p for p in range(len(gs.pieces)) if len(gs.pieces[p]) == 3]
    cena = [p for p in range(len(ga.pieces)) if len(ga.pieces[p]) == 4]
    cens = [p for p in range(len(gs.pieces)) if len(gs.pieces[p]) == 1]
    std_corners = {h: list(gs.pieces[h]) for h in cs}

    # Centre stickers all collapse to their piece's single ordinary sticker.
    sigma = {}
    for h in cena:
        target = gs.pieces[_PIECE_MAP[h]][0]
        for sticker in ga.pieces[h]:
            sigma[sticker] = target

    def propagate(mapping):
        changed = True
        while changed:
            changed = False
            for sticker, target in list(mapping.items()):
                for mi in range(len(aa)):
                    moved = pa[mi][sticker]
                    image = ps[_ATOM_MAP[mi]][target]
                    if moved in mapping:
                        if mapping[moved] != image:
                            return False
                    else:
                        mapping[moved] = image
                        changed = True
        return True

    def extend(mapping):
        mapping = dict(mapping)
        if not propagate(mapping):
            return None
        remaining = [h for h in ca if any(s not in mapping for s in ga.pieces[h])]
        if not remaining:
            return mapping
        h = remaining[0]
        for perm in itertools.permutations(std_corners[_PIECE_MAP[h]]):
            trial = dict(mapping)
            for sticker, target in zip(ga.pieces[h], perm):
                trial[sticker] = target
            found = extend(trial)
            if found is not None:
                return found
        return None

    sigma = extend(sigma)
    if sigma is None:
        raise ValueError('Skewb Ultimate sticker map is inconsistent')
    return (actual, standard, ga, gs, aa, sa, pa, ps, ca, cena, cens,
            tuple(sigma[s] for s in range(len(ga.stickers))))


def _perm_rank(perm):
    n = len(perm)
    rank = 0
    used = [False] * n
    for i, p in enumerate(perm):
        count = sum(1 for q in range(p) if not used[q])
        rank = rank * (n - i) + count
        used[p] = True
    return rank


@lru_cache(maxsize=1)
def _model():
    (actual, standard, ga, gs, aa, sa, pa, ps, ca, cena, cens, sigma) = _maps()
    (moves, order, dest, full, loc, a_idx, b_idx, c_idx,
     rank_a, rank_b, rank_c, table_a, table_b) = _skewb_model()
    assert len(_PIECE_MAP) == len(ga.pieces)
    assert len(_ATOM_MAP) == len(aa)
    for i, atom in enumerate(sa):
        assert (moves[i].axis, moves[i].layer, moves[i].amount) == (atom.axis, atom.layer, atom.amount)

    # Ordinary Skewb moves use the same atom order as _atoms(gs).
    sticker_trans = [bytes(dest[_ATOM_MAP[mi]][v] if v < _N else v
                           for v in range(256)) for mi in range(len(aa))]

    rank_a_b = {bytes(k): v for k, v in rank_a.items()}
    rank_b_b = {bytes(k): v for k, v in rank_b.items()}
    rank_c_b = {bytes(k): v for k, v in rank_c.items()}
    sub12 = bytes((v - 12) & 255 for v in range(256))
    sub24 = bytes((v - 24) & 255 for v in range(256))

    cena_slot = {pos: i for i, pos in enumerate(cena)}
    std_home_slot = {cens[j]: j for j in range(6)}
    centre_std_slot = {h: std_home_slot[_PIECE_MAP[h]] for h in cena}
    actual_slot_of_std = {}
    for j, pos in enumerate(cena):
        actual_slot_of_std[std_home_slot[_PIECE_MAP[pos]]] = j

    inverse = []
    for perm in pa:
        inv = [0] * len(perm)
        for i, j in enumerate(perm):
            inv[j] = i
        inverse.append(tuple(inv))

    def moved_pattern(h, slot, pattern, mi):
        here = ga.pieces[cena[slot]]
        perm = pa[mi]
        there_slot = cena_slot[ga.stickers[perm[here[0]]].piece]
        there = ga.pieces[cena[there_slot]]
        old_slot = {s: k for k, s in enumerate(here)}
        inv = inverse[mi]
        return there_slot, tuple(pattern[old_slot[inv[s]]] for s in there)

    # Each centre has exactly two reachable flips at every position.
    patterns = {}
    for h in cena:
        start = (cena_slot[h], (0, 1, 2, 3))
        seen = {start}
        queue = deque([start])
        while queue:
            slot, pattern = queue.popleft()
            patterns.setdefault((h, slot), set()).add(pattern)
            for mi in range(len(aa)):
                other = moved_pattern(h, slot, pattern, mi)
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
    order_pattern = {key: sorted(values) for key, values in patterns.items()}
    index_pattern = {key: {p: i for i, p in enumerate(values)}
                     for key, values in order_pattern.items()}

    next_flip = []
    for mi in range(len(aa)):
        per_move = []
        for h in cena:
            per_home = []
            for slot in range(6):
                row = []
                for bit, pattern in enumerate(order_pattern[(h, slot)]):
                    there, other = moved_pattern(h, slot, pattern, mi)
                    row.append(index_pattern[(h, there)][other])
                per_home.append(row)
            per_move.append(per_home)
        next_flip.append(per_move)

    identity = (0, 1, 2, 3)
    goal_bit = {cena_slot[h]: index_pattern[(h, cena_slot[h])][identity]
                for h in cena}
    goal_code = 0
    for slot, bit in goal_bit.items():
        if bit:
            goal_code |= 1 << slot

    slot_dest = []
    for mi in range(len(aa)):
        row = []
        for slot, pos in enumerate(cena):
            sticker = ga.pieces[pos][0]
            row.append(cena_slot[ga.stickers[pa[mi][sticker]].piece])
        slot_dest.append(row)

    perms = list(itertools.permutations(range(6)))
    rank_of = {p: i for i, p in enumerate(perms)}
    identity_rank = rank_of[tuple(range(6))]
    goal_state = identity_rank * 64 + goal_code

    size = 720 * 64
    dist = bytearray([255]) * size
    dist[goal_state] = 0
    centre_next = [array('H', [0]) * size for _ in range(len(aa))]
    queue = deque([(tuple(range(6)), goal_code)])
    while queue:
        perm, code = queue.popleft()
        state = rank_of[perm] * 64 + code
        depth = dist[state] + 1
        for mi in range(len(aa)):
            nperm = [0] * 6
            ncode = 0
            for slot in range(6):
                home = perm[slot]
                bit = (code >> home) & 1
                nperm[slot_dest[mi][slot]] = home
                if next_flip[mi][home][slot][bit]:
                    ncode |= 1 << home
            other = rank_of[tuple(nperm)] * 64 + ncode
            centre_next[mi][state] = other
            if dist[other] == 255:
                dist[other] = depth
                queue.append((tuple(nperm), ncode))

    return (aa, pa, sigma, loc, full, sticker_trans, rank_a_b, rank_b_b,
            rank_c_b, table_a, table_b, sub12, sub24, dist, centre_next,
            goal_state, rank_of, cena, cena_slot, centre_std_slot,
            actual_slot_of_std, order_pattern, index_pattern, goal_bit,
            goal_code, slot_dest, ga)


def _body_state(cube, sigma, loc, full):
    state = identify(cube)
    result = [None] * len(full)
    for sticker, current in enumerate(state):
        result[loc[sigma[sticker]]] = loc[sigma[current]]
    if sorted(result) != list(range(len(full))):
        raise ValueError('Skewb Ultimate body projection is invalid')
    return bytes(result)


def _centre_code(cube, ga, cena, cena_slot, order_pattern, index_pattern):
    state = identify(cube)
    code = 0
    for home in cena:
        slot = cena_slot[ga.stickers[state[ga.pieces[home][0]]].piece]
        here = ga.pieces[cena[slot]]
        inverse = {state[s]: s for s in ga.pieces[home]}
        home_slot = {s: i for i, s in enumerate(ga.pieces[home])}
        pattern = tuple(home_slot[inverse[s]] for s in here)
        try:
            bit = index_pattern[(home, slot)][pattern]
        except KeyError:
            raise ValueError('Skewb Ultimate centre orientation is invalid')
        if bit:
            code |= 1 << cena_slot[home]
    return code


def _centre_state(st, code, rank_of, cena, cena_slot, centre_std_slot,
                  actual_slot_of_std):
    perm = [None] * 6
    for home in cena:
        index = centre_std_slot[home]
        slot = actual_slot_of_std[st[24 + index] - 24]
        perm[slot] = cena_slot[home]
    return rank_of[tuple(perm)] * 64 + code


def solve_skewb_ultimate(cube, cancel=None, progress=None):
    if cube.is_solved():
        return ()
    try:
        return _solve(cube, cancel)
    except (ValueError, KeyError, IndexError, AssertionError):
        from solver.polyhedral_reduction import solve_tetrahedral
        return solve_tetrahedral(cube, cancel, progress)


def _solve(cube, cancel):
    (aa, pa, sigma, loc, full, sticker_trans, rank_a, rank_b, rank_c,
     table_a, table_b, sub12, sub24, dist, centre_next, goal_state, rank_of,
     cena, cena_slot, centre_std_slot, actual_slot_of_std, order_pattern,
     index_pattern, goal_bit, goal_code, slot_dest, ga) = _model()
    start = _body_state(cube, sigma, loc, full)
    centre = _centre_code(cube, ga, cena, cena_slot, order_pattern,
                          index_pattern)
    state = _centre_state(start, centre, rank_of, cena, cena_slot,
                          centre_std_slot, actual_slot_of_std)
    goal_body = bytes(range(_N))

    def body_h(st):
        a = st[:12]
        b = st[12:24].translate(sub12)
        c = st[24:].translate(sub24)
        rc = rank_c[c]
        ha = table_a[rank_a[a] * 360 + rc]
        hb = table_b[rank_b[b] * 360 + rc]
        return ha if ha > hb else hb

    def heuristic(st, cs):
        h = body_h(st)
        hc = dist[cs]
        return h if h > hc else hc

    if start == goal_body and state == goal_state:
        return ()
    inverse = {}
    for i, move in enumerate(aa):
        inverse[i] = next(j for j, other in enumerate(aa)
                          if other == move.inverse(3))
    path = []
    nodes = [0]

    def search(st, cs, depth, bound, last_axis):
        nodes[0] += 1
        if nodes[0] & 4095 == 0 and cancel and cancel():
            raise InterruptedError()
        h = heuristic(st, cs)
        if depth + h > bound:
            return depth + h
        if st == goal_body and cs == goal_state:
            return -1
        key = (st, cs)
        seen = table.get(key)
        if seen is not None and seen <= depth:
            return bound + 1
        table[key] = depth
        minimum = 1 << 30
        children = []
        for mi in range(len(aa)):
            if aa[mi].axis == last_axis:
                continue
            nst = st.translate(sticker_trans[mi])
            ncs = centre_next[mi][cs]
            children.append((heuristic(nst, ncs), mi, nst, ncs))
        children.sort()
        for _, mi, nst, ncs in children:
            path.append(mi)
            result = search(nst, ncs, depth + 1, bound, aa[mi].axis)
            if result == -1:
                return -1
            if result < minimum:
                minimum = result
            path.pop()
        return minimum

    bound = heuristic(start, state)
    while bound <= 40:
        if cancel and cancel():
            raise InterruptedError()
        table = {}
        result = search(start, state, 0, bound, -1)
        if result == -1:
            break
        if result >= (1 << 30):
            raise ValueError('Skewb Ultimate state is not solvable')
        bound = result
    else:
        raise ValueError('Skewb Ultimate search exceeded the depth limit')

    word = tuple(aa[mi] for mi in path)
    replay = cube.clone()
    for move in word:
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError('Skewb Ultimate solution replay failed')
    return word
