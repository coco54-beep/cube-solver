"""Native-ring reduction for high-order minxes.

The legacy high-order solver decomposes every piece orbit into conjugate
three-cycles, which costs a long setup for each three pieces. This module
matches how a solver works by hand:

1. A beam search over native layer turns. A native turn is a ring of five
   centres/edges, so a dozen turns can place a large fraction of every orbit
   at once.
2. The remaining permutation is finished with the same conjugate three-cycles
   the legacy solver uses, so the setup work only has to cover the residual.
3. Corner orientation is repaired at the end with a pure corner-twist gadget
   transported to the required triples. Twist states live in an abelian group
   (``Z_3`` per corner), so a small beam over the twist vectors reaches zero.

Every stage verifies its own replay; ``solve_high_minx`` falls back to the
legacy solver if any stage fails, so a caller always gets a correct solution.
"""
from itertools import combinations
from functools import lru_cache
import json
from operator import eq
from pathlib import Path
from random import Random
from time import monotonic
import zlib

from cube.polyhedral import Move

from solver.polyhedral import (apply_word, compose, identify, inverse,
                               inverse_word, piece_orbits, simplify)
from solver.polyhedral_reduction import (_SHORT_PRIMITIVE, Transports,
                                         joined_length, orbit_word, primitives)
from solver.nxn_orbits import three_cycles

#: Beam width/depth for the native-ring stage.
_BEAM_WIDTH = 64
_BEAM_DEPTH = 28
#: Beam width/depth for the corner-twist stage.
_TWIST_WIDTH = 256
_TWIST_DEPTH = 8


def _macro_cost(macros):
    return sum(len(word) for word, _ in macros.values())


def _native_moves(cube):
    g = cube.geometry
    return [Move(mv.axis, mv.layer, k * g.spec.step(mv.axis))
            for mv in cube.moves() for k in range(1, g.spec.turn_order)]


def _checked(cancel):
    if cancel is not None and cancel():
        raise InterruptedError()


def native_beam(work, positions, cancel=None, progress=None,
                width=_BEAM_WIDTH, max_depth=_BEAM_DEPTH,accelerated=True):
    """Greedily maximise the number of solved pieces with native ring turns."""
    g = work.geometry
    index = {p: i for i, p in enumerate(positions)}
    m = len(positions)
    combinations=[tuple(sorted(g.stickers[s].face for s in g.pieces[p])) for p in positions]
    entered=[tuple(sorted(work.colors[s] for s in g.pieces[p])) for p in positions]
    codes={value:i for i,value in enumerate(dict.fromkeys(combinations+entered))}
    if len(codes)>256:
        raise ValueError('Native-ring colour encoding exceeds one byte')
    home=bytes(codes[value] for value in combinations)
    colors=bytes(codes[value] for value in entered)
    invs, atoms, rings = [], [], []
    seen = set()
    identity = tuple(range(m))
    for mv in _native_moves(work):
        _checked(cancel)
        perm = g.permutation(mv)
        local = [index[g.stickers[perm[g.pieces[p][0]]].piece] for p in positions]
        inv = [0] * m
        for j in range(m):
            inv[local[j]] = j
        inv = tuple(inv)
        # Distinct powers and layers often act identically on the movable
        # pieces; fold them so the beam branching reflects real choices only.
        if inv == identity or inv in seen:
            continue
        seen.add(inv)
        invs.append(inv)
        atoms.append(mv)
        # A native turn only permutes a small ring of positions, so scores and
        # states can be updated there instead of over every piece.
        rings.append(tuple((i, inv[i]) for i in range(m) if inv[i] != i))

    if not invs or not positions:
        return []
    np=None
    if accelerated:
        try:
            import numpy as np
        except ImportError:
            pass
    if np is not None:
        indices=np.asarray(invs,dtype=np.uint16 if m<=65536 else np.uint32)
        reference=np.frombuffer(home,dtype=np.uint8)
        # Release Python tuple/set copies once the compact lookup is ready.
        invs_count=len(invs)
        invs.clear()
        seen.clear()
    else:
        invs_count=len(invs)

    def correct(state):
        return sum(map(eq,state,home))

    frontier = {colors: ((), correct(colors))}
    best_count, best_path = correct(colors), ()
    for _ in range(max_depth):
        _checked(cancel)
        nxt = {}
        for state,(path,score) in frontier.items():
            _checked(cancel)
            if np is not None:
                candidates=np.frombuffer(state,dtype=np.uint8)[indices]
                scores=(candidates==reference).sum(axis=1)
            for ai in range(invs_count):
                if np is not None:
                    ns=candidates[ai].tobytes()
                    next_score=int(scores[ai])
                else:
                    ring=rings[ai]
                    ns=bytearray(state)
                    for i,j in ring:
                        ns[i]=state[j]
                    next_score=score+sum((ns[i]==home[i])-(state[i]==home[i])
                                         for i,_ in ring)
                    ns=bytes(ns)
                if ns not in nxt:
                    # Delay constructing complete paths until a candidate
                    # survives the beam. Keep the original stable tie order.
                    nxt[ns]=(next_score,path,ai)
            # Only the best ``width`` unique states can survive this level.
            # Prune after each parent instead of retaining width * actions
            # complete sticker states on high orders. Stable sorting preserves
            # the original first-seen tie order; a discarded state cannot beat
            # the retained threshold if encountered again later.
            if len(nxt)>width:
                nxt=dict(sorted(nxt.items(),key=lambda kv:-kv[1][0])[:width])
        ranked=sorted(nxt.items(),key=lambda kv:-kv[1][0])[:width]
        frontier={s:(path+(atoms[ai],),score) for s,(score,path,ai) in ranked}
        winner=next(iter(frontier.values()))
        bc=winner[1]
        if bc > best_count:
            best_count,best_path=bc,winner[0]
        if best_count == m:
            break
    for mv in best_path:
        work.apply_move(mv)
    return list(best_path)


def _orbit_plan(work, orbit, base, primitive, state, prefix, cancel, search_budget):
    g = work.geometry
    indexes = {p: i for i, p in enumerate(orbit)}
    destination = [None] * len(orbit)
    for home in orbit:
        position = g.stickers[state[g.pieces[home][0]]].piece
        destination[indexes[position]] = indexes[home]
    if not three_cycles(destination):
        return None
    transports = Transports(work, orbit, base, cancel, both_directions=True)
    return orbit_word(transports, orbit, destination, primitive, prefix,
                      alternatives=len(g.pieces[orbit[0]]) == 1,
                      search_budget=search_budget)


def solve_orbits(work, targets, cancel=None, progress=None, search_budget=0.3):
    """Finish the residual permutation of each orbit with conjugate three-cycles.

    Odd orders have orbits whose isolating commutator is long. As in the legacy
    solver, those orbits are solved first while protecting the already-solved
    orbits, which shortens their macros; the staged plan is adopted only when it
    lowers the total macro cost.
    """
    g = work.geometry
    order = g.spec.turn_order
    from solver.minx_plans import orbit_plan
    prepared=orbit_plan(work,targets)
    if prepared is not None and prepared[2]:
        macros,solve_order,_=prepared
        solution=[]
        for stage,index in enumerate(solve_order):
            _checked(cancel)
            primitive,base=macros[index]
            word=_orbit_plan(work,targets[index],base,primitive,identify(work),
                             solution,cancel,search_budget)
            if word:
                for move in word:work.apply_move(move)
                solution.extend(word)
            if progress:progress(stage+1,len(solve_order))
        return solution
    baseline = prepared[0] if prepared is not None else primitives(work,targets,cancel)
    staged, solve_order = None, None
    if prepared is None and any(len(baseline[i][0]) > _SHORT_PRIMITIVE for i in baseline):
        solve_order = sorted(targets, key=lambda i: -len(baseline[i][0]))
        guarded, protected = set(), {}
        for index in solve_order:
            protected[index] = set(guarded)
            guarded.update(s for p in targets[index] for s in g.pieces[p])
        try:
            staged = primitives(work, targets, cancel, protected=protected)
        except ValueError:
            staged = None
    if staged is not None and _macro_cost(staged) < _macro_cost(baseline):
        solution = []
        for index in solve_order:
            _checked(cancel)
            orbit = targets[index]
            primitive, base = staged[index]
            word = _orbit_plan(work, orbit, base, primitive, identify(work),
                               solution, cancel, search_budget)
            if word is None:
                continue
            for mv in word:
                work.apply_move(mv)
            solution.extend(word)
        return solution
    state = identify(work)
    plans = []
    for index, orbit in targets.items():
        _checked(cancel)
        primitive, base = baseline[index]
        word = _orbit_plan(work, orbit, base, primitive, state, (), cancel, search_budget)
        if word is None:
            continue
        plans.append((index, word))
    solution, prefix, ordered = [], [], []
    pending = list(plans)
    while pending:
        _checked(cancel)
        choice = min(range(len(pending)),
                     key=lambda i: joined_length(prefix, pending[i][1], order))
        _, word = pending.pop(choice)
        ordered.append(word)
        prefix=simplify(tuple(prefix)+word,order)
    for word in ordered:
        for mv in word:
            work.apply_move(mv)
        solution.extend(word)
    return solution


def _twist_vector(perm, g, corners):
    vec = []
    for p in corners:
        order = g.pieces[p]
        image = {s: perm[s] for s in order}
        k = next(kk for kk in range(3)
                 if all(image[order[(i + kk) % 3]] == order[i] for i in range(3)))
        vec.append(k % 3)
    return tuple(vec)


def _current_twist(colors, g, corners):
    vec = []
    for p in corners:
        order = g.pieces[p]
        cur = [colors[s] for s in order]
        home = [g.stickers[s].face for s in order]
        k = next(kk for kk in range(3)
                 if all(cur[i] == home[(i + kk) % 3] for i in range(3)))
        vec.append(k % 3)
    return tuple(vec)


_GADGET_CACHE = {}
_GADGET_ASSET = Path(__file__).parent / 'data' / 'minx_twist_gadgets.bin'


@lru_cache(maxsize=1)
def _gadget_asset():
    if _GADGET_ASSET.exists():
        return json.loads(zlib.decompress(_GADGET_ASSET.read_bytes()))
    return {}


def build_twist_gadget(cube, corners, budget=2.0):
    """Return (word, base_triple, base_vector) for a pure 3-corner twist.

    A shorter toy twist directly shortens the whole corner stage, so a short
    randomized search is combined with the deterministic commutator scan. The
    result depends only on the order's geometry, so it is cached per order and
    otherwise loaded from the prepared asset.
    """
    key = cube.n
    if key in _GADGET_CACHE:
        return _GADGET_CACHE[key]
    asset = _gadget_asset().get(str(key))
    if asset is not None:
        result = (tuple(Move(*m) for m in asset['word']), tuple(asset['base']), None)
        _GADGET_CACHE[key] = result
        return result
    g = cube.geometry
    order = g.spec.turn_order
    corner_stickers = {s for p in corners for s in g.pieces[p]}
    pword, _ = primitives(cube, {0: corners}, None)[0]
    base_perm = apply_word(g, pword)
    identity = tuple(range(len(g.stickers)))

    def pure(perm):
        if any(perm[s] != s for s in range(len(g.stickers)) if s not in corner_stickers):
            return False
        return all({perm[s] for s in g.pieces[p]} == set(g.pieces[p]) for p in corners)

    atoms = _native_moves(cube)
    toys = []

    def offer(word, perm):
        for _, existing in toys:
            if existing == perm:
                return
        toys.append((word, perm))

    for m1 in atoms:
        m1p = g.permutation(m1)
        g1 = compose(compose(m1p, base_perm), inverse(m1p))
        w1 = (m1,) + pword + (m1.inverse(order),)
        for m2 in atoms:
            if m2.axis == m1.axis:
                continue
            m2p = g.permutation(m2)
            g2 = compose(compose(m2p, base_perm), inverse(m2p))
            w2 = (m2,) + pword + (m2.inverse(order),)
            base = compose(compose(compose(g1, g2), inverse(g1)), inverse(g2))
            cur = identity
            for power in range(1, 21):
                cur = compose(cur, base)
                if cur == identity:
                    break
                if pure(cur) and any(_twist_vector(cur, g, corners)):
                    offer(simplify((w1 + w2 + inverse_word(w1, order) +
                                    inverse_word(w2, order)) * power, order), cur)
                    break

    # Randomised commutators of conjugated three-cycles reach much shorter
    # twists than the single-move scan above.
    if budget > 0:
        rng = Random(12345)
        started = monotonic()

        def rand_setup(maxlen):
            out, last = [], -1
            for _ in range(rng.randint(1, maxlen)):
                options = [m for m in atoms if m.axis != last]
                m = rng.choice(options)
                out.append(m)
                last = m.axis
            return tuple(out)

        while monotonic() - started < budget:
            s1, s2 = rand_setup(3), rand_setup(3)
            p1, p2 = apply_word(g, s1), apply_word(g, s2)
            a = compose(compose(p1, base_perm), inverse(p1))
            b = compose(compose(p2, base_perm), inverse(p2))
            cand = compose(compose(compose(a, b), inverse(a)), inverse(b))
            wa = s1 + pword + inverse_word(s1, order)
            wb = s2 + pword + inverse_word(s2, order)
            comm = wa + wb + inverse_word(wa, order) + inverse_word(wb, order)
            cur = cand
            for power in range(1, 7):
                if power > 1:
                    cur = compose(cur, cand)
                if cur == identity:
                    break
                if pure(cur) and any(_twist_vector(cur, g, corners)):
                    offer(simplify(comm * power, order), cur)
                    break

    def add(a, b):
        return tuple((x + y) % 3 for x, y in zip(a, b))

    # A shorter toy is only useful if two of its conjugates still combine into
    # a pure three-corner twist, so try toys shortest-first and keep the first
    # that works.
    result = None
    for toy_word, toy_perm in sorted(toys, key=lambda item: len(item[0]))[:40]:
        candidates = [((), _twist_vector(toy_perm, g, corners))]
        for m in atoms:
            mp = g.permutation(m)
            perm = compose(compose(mp, toy_perm), inverse(mp))
            candidates.append(((m,), _twist_vector(perm, g, corners)))
        for s1, v1 in candidates:
            for s2, v2 in candidates:
                vec = add(v1, v2)
                support = [i for i, x in enumerate(vec) if x]
                if len(support) == 3 and all(vec[i] == 1 for i in support):
                    word = (s1 + tuple(toy_word) + inverse_word(s1, order) +
                            s2 + tuple(toy_word) + inverse_word(s2, order))
                    result = (simplify(word, order),
                              tuple(corners[i] for i in support), vec)
                    break
            if result:
                break
        if result:
            break
    _GADGET_CACHE[key] = result
    return result


def solve_twist(work, corners, gadget, cancel=None, progress=None,
                width=_TWIST_WIDTH, max_depth=_TWIST_DEPTH):
    """Zero the corner twist with transported pure-twist gadgets."""
    g = work.geometry
    order = g.spec.turn_order
    p3_word, p3_base, _ = gadget
    transports = Transports(work, corners, p3_base, cancel, both_directions=True)
    ops = []
    for triple in combinations(range(len(corners)), 3):
        _checked(cancel)
        target = tuple(corners[i] for i in triple)
        word = transports.conjugate(target, p3_word)
        op = apply_word(g, word)
        ops.append((_twist_vector(op, g, corners), word))
        ops.append((tuple((-x) % 3 for x in ops[-1][0]), inverse_word(word, order)))

    def wrong(vec):
        return sum(1 for x in vec if x)

    start = _current_twist(work.colors, g, corners)
    if wrong(start) == 0:
        return []
    frontier = {start: ()}
    for depth in range(1, max_depth + 1):
        _checked(cancel)
        nxt = {}
        for vec, path in frontier.items():
            for tvec, word in ops:
                nv = tuple((a + b) % 3 for a, b in zip(vec, tvec))
                if nv not in nxt:
                    nxt[nv] = path + (word,)
        ranked = sorted(nxt.items(), key=lambda kv: wrong(kv[0]))[:width]
        frontier = {v: p for v, p in ranked}
        if wrong(ranked[0][0]) == 0:
            applied = []
            for word in ranked[0][1]:
                for mv in word:
                    work.apply_move(mv)
                applied.extend(word)
            return applied
    raise ValueError('corner twist was not reached')


def solve_reduced(cube, cancel=None, progress=None, *, _beam=None):
    work = cube.entered() if _beam is None else _beam[0]
    g = work.geometry
    orbits = piece_orbits(cube.puzzle_kind, cube.n)
    corners = next((o for o in orbits if len(g.pieces[o[0]]) == 3), None)
    positions = [p for o in orbits if len(o) > 1 for p in o]
    targets = {i: o for i, o in enumerate(orbits) if len(o) > 1}
    # A wide beam fixes most pieces in a dozen turns, but the per-level cost is
    # width * atoms * pieces. Shrink the width on the large orders so the stage
    # stays responsive while still covering most of the solved pieces.
    m = len(positions)
    width = _BEAM_WIDTH if m <= 900 else max(24, 49152 // m)
    solution = []
    if _beam is None:
        solution.extend(native_beam(work, positions, cancel, progress, width=width))
    else:
        solution.extend(_beam[1])
    solution.extend(solve_orbits(work, targets, cancel, progress))
    if corners is not None:
        gadget = build_twist_gadget(work, corners)
        if gadget is not None:
            solution.extend(solve_twist(work, corners, gadget, cancel, progress))
    if not work.is_solved():
        # A few flipped core edges (odd orders) cannot be isolated by a pure
        # gadget. The residual is tiny, so finish it with the legacy solve and
        # append the few moves it needs.
        from solver.polyhedral_reduction import _solve_high_minx_legacy
        solution.extend(_solve_high_minx_legacy(work, cancel, progress))
    check = cube.entered()
    for move in solution:
        check.apply_move(move)
    if not check.is_solved():
        raise ValueError('High-order minx reduction replay failed')
    return simplify(tuple(solution), g.spec.turn_order)
