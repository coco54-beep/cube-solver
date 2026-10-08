"""Coordinate-based commutators for variable order cubes.

Atoms are isolated slices (face, coordinate, quarter-turn count). They are
expanded to this application's wide-turn notation only at the public boundary.
No scramble history or cubie.home fields are used to identify entered pieces.
"""
from collections import Counter, defaultdict, deque
from itertools import permutations, product
from functools import lru_cache

from cube.coordinates import FACE_AXIS_SIGN, TURNS, coord_values, get_d_maxc
from cube.cube_n import CubeN


@lru_cache(maxsize=2)
def _solved(n):
    return CubeN.solved(n)


def inverse(seq):
    return [(f, v, (4 - c) % 4) for f, v, c in reversed(seq)]


def move_point(p, atom):
    f, v, count = atom
    if p[FACE_AXIS_SIGN[f][0]] == v:
        for _ in range(count):
            p = TURNS[f](*p)
    return p


def expand(seq, n):
    values = coord_values(n)
    result = []
    for face, coordinate, count in seq:
        ordered = sorted(values, reverse=FACE_AXIS_SIGN[face][1] > 0)
        k = ordered.index(coordinate) + 1
        suffix = {1: "", 2: "2", 3: "'"}[count]
        result.append((str(k) if k > 1 else "") + face + suffix)
        if k > 1:
            result.append((str(k - 1) if k > 2 else "") + face
                          + {1: "'", 2: "2", 3: ""}[count])
    return result


def generators(n, positions):
    _, m = get_d_maxc(n)
    inner = sorted({v for p in positions for v in p if abs(v) < m})
    atoms = [(f, sign * m, c) for f, (_, sign) in FACE_AXIS_SIGN.items()
             for c in (1, 2, 3)]
    atoms.extend((f, v, c) for f in ("R", "U", "F") for v in inner
                 for c in (1, 2, 3))
    return atoms


@lru_cache(maxsize=8)
def orbits(n, sticker_count):
    solved = _solved(n)
    remaining = {p for p, cb in solved.cubies.items()
                 if len(cb.stickers) == sticker_count}
    result = []
    while remaining:
        start = min(remaining)
        gen = generators(n, (start,))
        found, queue = {start}, deque([start])
        while queue:
            p = queue.popleft()
            for atom in gen:
                q = move_point(p, atom)
                if q not in found:
                    found.add(q)
                    queue.append(q)
        remaining.difference_update(found)
        result.append(tuple(sorted(found)))
    return tuple(result)


def parity(perm):
    visited = set()
    sign = 0
    for i in range(len(perm)):
        length, j = 0, i
        while j not in visited:
            visited.add(j)
            length += 1
            j = perm[j]
        if length:
            sign ^= (length - 1) % 2
    return sign


def three_cycles(perm):
    """Decompose pos→destination into forward cycles to apply to the cube."""
    if parity(perm):
        raise ValueError("Odd orbit permutation")
    work, result = list(perm), []

    def apply(trip):
        a, b, c = trip
        work[a], work[b], work[c] = work[c], work[a], work[b]
        result.append(trip)

    while any(i != v for i, v in enumerate(work)):
        cycles, visited = [], set()
        for i in range(len(work)):
            cycle, j = [], i
            while j not in visited:
                visited.add(j)
                cycle.append(j)
                j = work[j]
            if len(cycle) > 1:
                cycles.append(cycle)
        big = next((c for c in cycles if len(c) >= 3), None)
        if big:
            apply(tuple(big[:3]))
        else:
            (a, b), (c, d) = cycles[:2]
            apply((a, b, c))
            apply((a, d, c))
    return result


def rotations():
    for order in permutations(range(3)):
        swaps = sum(order[i] > order[j] for i in range(3) for j in range(i + 1, 3))
        for signs in product((-1, 1), repeat=3):
            if (-1) ** swaps * signs[0] * signs[1] * signs[2] == 1:
                yield lambda p, o=order, s=signs: tuple(s[i] * p[o[i]] for i in range(3))


def wing_permutation(cube, positions):
    """Wings with identical colors are distinguished by their orientation."""
    solved = _solved(cube.n)
    identities = {}
    rots = list(rotations())
    for home in positions:
        cb = solved.cubies[home]
        for rot in rots:
            key = (rot(home), tuple(sorted((rot(normal), color)
                                          for normal, color in cb.stickers.items())))
            index = positions.index(home)
            old = identities.setdefault(key, index)
            if old != index:
                raise ValueError("Ambiguous wing identity")
    result = []
    for p in positions:
        key = (p, tuple(sorted(cube.cubies[p].stickers.items())))
        if key not in identities:
            raise ValueError("nxn.error.wings")
        result.append(identities[key])
    if len(set(result)) != len(positions):
        raise ValueError("nxn.error.wings")
    return result


def center_permutation(cube, positions):
    solved = _solved(cube.n)
    homes = defaultdict(list)
    for i, p in enumerate(positions):
        homes[next(iter(solved.cubies[p].stickers.values()))].append(i)
    actual = [next(iter(cube.cubies[p].stickers.values())) for p in positions]
    expected = Counter({color: len(ids) for color, ids in homes.items()})
    if Counter(actual) != expected:
        raise ValueError("nxn.error.centers")
    result = [None] * len(positions)
    for i, color in enumerate(actual):
        if i in homes[color]:
            homes[color].remove(i)
            result[i] = i
    for i, color in enumerate(actual):
        if result[i] is None:
            result[i] = homes[color].pop()
    if parity(result):
        pair = next(((i, j) for i in range(len(actual)) for j in range(i + 1, len(actual))
                     if actual[i] == actual[j]), None)
        if pair is None:
            raise ValueError("nxn.error.centers")
        i, j = pair
        result[i], result[j] = result[j], result[i]
    return result


def _effect(n, atoms):
    solved = _solved(n)
    changed = {}
    for home, cb in solved.cubies.items():
        pos, stickers = home, cb.stickers
        for face, coordinate, count in atoms:
            if pos[FACE_AXIS_SIGN[face][0]] == coordinate:
                for _ in range(count):
                    pos = TURNS[face](*pos)
                    stickers = {TURNS[face](*normal): color for normal, color in stickers.items()}
        if pos != home or stickers != cb.stickers:
            changed[home] = (pos, len(cb.stickers))
    return changed


def primitive(n, positions, wings, cancel):
    """Construct and inspect an isolating commutator before using it."""
    _, m = get_d_maxc(n)
    inner = sorted({v for p in positions for v in p if abs(v) < m})
    candidates = []
    for a in inner:
        A = [("R", a, 1)]
        if wings:
            # [inner R, U' R U]: changes three wings in this orbit;
            # center side effects are handled after all wing orbits.
            B = [("U", m, 3), ("R", m, 1), ("U", m, 1)]
            candidates.append(A + B + inverse(A) + inverse(B))
        else:
            for b in inner:
                B = [("U", m, 1), ("R", b, 1), ("U", m, 3)]
                candidates.append(A + B + inverse(A) + inverse(B))
                # Alternative center commutator described by Chris Hardwick.
                A2 = [("R", a, 1), ("U", b, 1), ("R", a, 3)]
                B2 = [("U", m, 3)]
                candidates.append(A2 + B2 + inverse(A2) + inverse(B2))
    target = set(positions)
    for atoms in candidates:
        cancel()
        changed = _effect(n, atoms)
        affected = {p: q for p, (q, count) in changed.items()
                    if count == (2 if wings else 1)}
        if len(affected) != 3 or not set(affected) <= target:
            continue
        if any(count == 3 or (not wings and count != 1)
               for _, count in changed.values()):
            continue
        a = min(affected)
        b, c = affected[a], affected[affected[a]]
        if c == a or affected[c] != a:
            continue
        return atoms, (positions.index(a), positions.index(b), positions.index(c))
    raise RuntimeError("nxn.error.primitive")


def conjugates(n, positions, base, start, targets, cancel):
    """BFS on three markers, at most 24×23×22 states per orbit."""
    gen = generators(n, positions)
    indexes = {p: i for i, p in enumerate(positions)}
    maps = [tuple(indexes[move_point(p, atom)] for p in positions) for atom in gen]
    parents, queue = {start: None}, deque([start])
    remaining = set(targets)
    remaining.discard(start)
    visits = 0
    while queue and remaining:
        state = queue.popleft()
        visits += 1
        if visits % 128 == 0:
            cancel()
        for i, mapping in enumerate(maps):
            nxt = tuple(mapping[p] for p in state)
            if nxt not in parents:
                parents[nxt] = (state, i)
                queue.append(nxt)
                remaining.discard(nxt)
    if remaining:
        raise RuntimeError("nxn.error.setup")
    result = []
    for target in targets:
        setup, cur = [], target
        while parents[cur] is not None:
            cur, i = parents[cur]
            setup.append(gen[i])
        setup.reverse()
        result.append(inverse(setup) + base + setup)
    return result
