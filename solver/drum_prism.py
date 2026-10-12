"""Prepared state solvers for the War Drum and triangular prism families."""
from functools import lru_cache
import json
from pathlib import Path
from random import Random
from time import monotonic
import zlib

from cube.polyhedral import Move
from solver.lattice_data import geometry_key
from solver.polyhedral import (identify, inverse_word, compose, inverse,
                               piece_orbits, simplify)


def core_points(cube):
    g = cube.geometry
    if cube.puzzle_kind == 'pentahedron':
        return tuple(reversed(range(len(g.stickers))))
    points = tuple(s for orbit in piece_orbits(cube.puzzle_kind, cube.n)
                   if len(orbit) <= 6 or len(g.pieces[orbit[0]]) >= 3
                   for p in orbit for s in g.pieces[p])
    # The stabilizer walks from the end of its base. Place hexagon/core edge
    # constraints there first; the other order produces very long relations.
    return tuple(sorted(points, key=lambda s: (g.stickers[s].face,
                                               g.stickers[s].piece), reverse=True))


@lru_cache(maxsize=1)
def _assets():
    path = Path(__file__).parent / 'data' / 'drum_prism.bin'
    return json.loads(zlib.decompress(path.read_bytes()))


def _record(cube):
    record = _assets().get(f'{cube.puzzle_kind}:{cube.n}')
    if (not record or record['geometry'] != geometry_key(cube.geometry)
            or tuple(record['points']) != core_points(cube)):
        raise ValueError('Puzzle solver data does not match the model')
    return record


def _labeled_core(cube, record, cancel, progress):
    points = record['points']
    index = {s: i for i, s in enumerate(points)}
    full = identify(cube)
    state = tuple(index[full[s]] for s in points)
    solution = []
    for k in range(len(points)-1, -1, -1):
        if cancel and cancel():
            raise InterruptedError()
        if state[k] != k:
            entry = record['rows'][k].get(str(state[k]))
            if entry is None:
                return None
            permutation, word = entry
            state = compose(state, inverse(permutation))
            solution.extend(inverse_word(tuple(Move(*m) for m in word),
                                         cube.geometry.spec.turn_order))
        if progress:
            progress(len(points)-k, len(points))
    return simplify(solution, cube.geometry.spec.turn_order)


def _colored_core(cube, record, cancel, progress):
    """Resolve indistinguishable centres without inventing an orbit parity.

    Each transversal fixes all later base points. Search only entries that
    put the required colour at the current point, then recurse on the prefix.
    This is a finite coset search in the full generated move group, including
    the coupling between prism half turns and triangle turns.
    """
    points = record['points']
    if cancel and cancel():
        raise InterruptedError()
    goal = tuple(cube.geometry.stickers[s].face for s in points)
    initial = tuple(cube.colors[s] for s in points)
    rows = record['rows']
    failed = set()
    frames = []
    state = initial
    k = len(points)-1
    calls = 0
    while True:
        calls += 1
        if calls % 64 == 0 and cancel and cancel():
            raise InterruptedError()
        if k < 0:
            return simplify((Move(*m).inverse(cube.geometry.spec.turn_order)
                             for _, _, _, entry in frames
                             for m in reversed(entry[1])), cube.geometry.spec.turn_order)
        signature = (k, state[:k+1])
        choices = []
        if signature not in failed:
            for permutation, word in rows[k].values():
                if state[permutation[k]] == goal[k]:
                    nxt = tuple(state[p] for p in permutation)
                    score = sum(a != b for a, b in zip(nxt[:k], goal[:k]))
                    choices.append((score, len(word), nxt, (permutation, word)))
            choices.sort(key=lambda item: item[:2])
        if choices:
            _, _, nxt, entry = choices.pop(0)
            frames.append((k, state, choices, entry))
            state = nxt
            k -= 1
            if progress and calls % 64 == 0:
                progress(len(points)-k, len(points))
            continue
        failed.add(signature)
        while frames:
            parent_k, parent_state, choices, _ = frames.pop()
            if choices:
                _, _, nxt, entry = choices.pop(0)
                frames.append((parent_k, parent_state, choices, entry))
                state, k = nxt, parent_k-1
                break
            failed.add((parent_k, parent_state[:parent_k+1]))
        else:
            raise ValueError('The entered puzzle is not a legal state')


def _core_atoms(cube):
    """Every non-identity power of every legal layer turn."""
    order = cube.geometry.spec.turn_order
    return [Move(m.axis, m.layer, (cube.geometry.spec.step(m.axis) * power) % order)
            for m in cube.moves() for power in range(1, order)]


def _core_word(cube, record):
    word = _labeled_core(cube, record, None, None)
    if word is None:
        word = _colored_core(cube, record, None, None)
    return list(word)


def _core_solved(cube, word, points):
    work = cube.entered()
    for move in word:
        work.apply_move(move)
    g = work.geometry
    return all(work.colors[s] == g.stickers[s].face for s in points)


#: Wall-clock budget for the core improvement search. The stabiliser expansion
#: is greedy and highly redundant, so re-expanding slightly perturbed states
#: cancels most of the transversals. Core re-expansion is milliseconds, so many
#: iterations fit in this budget.
_CORE_OPTIMIZE_BUDGET = 0.5
_CORE_OPTIMIZE_MIN = 20


def _optimize_core(cube, record, cancel=None, budget=_CORE_OPTIMIZE_BUDGET):
    """Re-expand the stabiliser core from perturbed states, keeping the best.

    Every accepted word is replayed and checked against the core stickers, so a
    caller can always fall back to the direct expansion.
    """
    order = cube.geometry.spec.turn_order
    points = record['points']
    best = _core_word(cube, record)
    if budget <= 0 or len(best) <= _CORE_OPTIMIZE_MIN:
        return best
    atoms = _core_atoms(cube)
    if not atoms:
        return best
    seed = 0
    for move in best:
        seed = (seed * 131 + move.axis * 7 + move.layer * 3 + move.amount) & 0xffffffff
    rng = Random(seed)
    deadline = monotonic() + budget
    while monotonic() < deadline:
        if cancel is not None and cancel():
            raise InterruptedError()
        cut = rng.randrange(0, len(best))
        prefix = list(best[:cut]) + [rng.choice(atoms)
                                     for _ in range(rng.choice((1, 2, 2, 3, 3, 4)))]
        probe = cube.entered()
        for move in prefix:
            probe.apply_move(move)
        try:
            word = _core_word(probe, record)
        except (ValueError, InterruptedError):
            continue
        candidate = simplify(tuple(prefix) + tuple(word), order)
        if len(candidate) < len(best) and _core_solved(cube, candidate, points):
            best = list(candidate)
    return best


def solve_drum_prism(cube, cancel=None, progress=None, verify=True):
    record = _record(cube)
    identify(cube)  # Colour counts, physical piece combinations and handedness.
    if cube.puzzle_kind == 'war_drum':
        # The War Drum core is expanded here; the pentahedron re-expands its
        # own core in solver.pentahedron_high, so it must stay raw.
        word = _optimize_core(cube, record, cancel)
    else:
        word = _labeled_core(cube, record, cancel, progress)
        if word is None:
            word = _colored_core(cube, record, cancel, progress)
    if not verify and cube.puzzle_kind != 'war_drum':
        return word
    work = cube.entered()
    solution = list(word)
    for i, move in enumerate(word):
        if i % 64 == 0 and cancel and cancel():
            raise InterruptedError()
        work.apply_move(move)
    if cube.puzzle_kind == 'war_drum':
        from solver.polyhedral_reduction import Transports, orbit_word
        for stage, (orbit_id, data) in enumerate(record['cycles'].items()):
            if cancel and cancel():
                raise InterruptedError()
            orbit = piece_orbits(cube.puzzle_kind, cube.n)[int(orbit_id)]
            state = identify(work)
            indexes = {p: i for i, p in enumerate(orbit)}
            destination = [None]*len(orbit)
            for home in orbit:
                pos = work.geometry.stickers[state[work.geometry.pieces[home][0]]].piece
                destination[indexes[pos]] = indexes[home]
            primitive = tuple(Move(*m) for m in data['word'])
            transports = Transports(work, orbit, tuple(data['base']), cancel,
                                    both_directions=True)
            moves = orbit_word(transports, orbit, destination, primitive, solution,
                               alternatives=len(work.geometry.pieces[orbit[0]]) == 1)
            for move in moves:
                work.apply_move(move)
            solution.extend(moves)
            if progress:
                progress(stage+1, len(record['cycles']))
    if not work.is_solved():
        raise ValueError('Puzzle solution replay failed')
    return simplify(solution, cube.geometry.spec.turn_order)
