"""Solve Mastermorphix cubies and the six visible center orientations.

Center-only generators follow Jaap Scherphuis's Supergroup construction:
https://www.jaapsch.net/puzzles/theory.htm (Supergroup).
They are conjugated by proper cube rotations, never reflection.
"""

from functools import lru_cache
from heapq import heappop, heappush
import time

from cube.mastermorphix import (
    MastermorphixCube, ROTATIONS, transform, normalize_input,
    position_kind, piece_colors, equivalent_placements,
)
from cube.coordinates import FACE_NORMALS, FACE_AXIS_SIGN
from cube.conversion import cubies_to_facelets
from cube.notation import parse_move_str, suffix_for_count
from solver.result import SolveResult, SolveStage


@lru_cache(maxsize=32)
def _outer_turn(move):
    face, _, count = parse_move_str(move, allow_wide=False)
    return face, FACE_AXIS_SIGN[face][0], count


def _compact_moves(moves):
    """Combine outer-face turns, commuting opposite faces within one axis.

    This preserves the shaped pieces and visible center frames. It never
    substitutes wide turns or whole-puzzle rotations.
    """
    blocks = []
    for move in moves:
        face, axis, count = _outer_turn(move)
        if not blocks or blocks[-1][0] != axis:
            blocks.append((axis, {}))
        counts = blocks[-1][1]
        counts[face] = (counts.get(face, 0) + count) % 4
        if not counts[face]:
            del counts[face]
        if not counts:
            blocks.pop()
    return [face + suffix_for_count(count)
            for _, counts in blocks for face, count in counts.items()]


@lru_cache(maxsize=1)
def _center_generators():
    face_for_normal = {n: face for face, n in FACE_NORMALS.items()}
    pair = "R L' F B' U D' R' U' D F' B R' L U".split()
    half = "R L U2 R' L' U R L U2 R' L' U".split()
    generators = {}
    baseline = MastermorphixCube.solved()

    def retain(delta, moves):
        moves = tuple(_compact_moves(moves))
        generators.setdefault(delta, set()).add(moves)

    for frame in ROTATIONS:
        mapping = {f: face_for_normal[transform(frame, n)] for f, n in FACE_NORMALS.items()}
        for algorithm in (pair, half):
            moves = tuple(mapping[m[0]] + m[1:] for m in algorithm)
            probe = MastermorphixCube.solved()
            probe.apply_moves(moves)
            # A bad notation convention must fail rather than corrupt a solve.
            if any(c.home != c.pos or c.stickers != baseline.cubies[p].stickers
                   for p, c in probe.cubies.items()):
                raise RuntimeError("Center generator changed movable pieces")
            delta = probe.center_twists()
            retain(delta, moves)
            inverse = tuple(m[0] + ("2" if m.endswith("2") else ("" if m.endswith("'") else "'"))
                            for m in reversed(moves))
            retain(tuple((-v) % 4 for v in delta), inverse)
    return {delta: tuple(sorted(words, key=lambda word: (len(word), word)))
            for delta, words in generators.items()}


@lru_cache(maxsize=1)
def _center_paths():
    generators = _center_generators()
    zero = (0,) * 6
    paths = {zero: None}
    costs = {zero: 0}
    queue = [(0, zero)]
    while queue:
        cost, state = heappop(queue)
        if cost != costs[state]:
            continue
        for delta, alternatives in generators.items():
            moves = alternatives[0]
            nxt = tuple((a+b) % 4 for a, b in zip(state, delta))
            candidate_cost = cost + len(moves)
            if candidate_cost < costs.get(nxt, float("inf")):
                costs[nxt] = candidate_cost
                paths[nxt] = (state, moves)
                heappush(queue, (candidate_cost, nxt))
    if len(paths) != 2048:
        raise RuntimeError("Center generators do not cover the supercube subgroup")
    return paths


@lru_cache(maxsize=2048)
def _center_chunks(twists):
    target = tuple((-v) % 4 for v in twists)
    paths = _center_paths()
    if target not in paths:
        raise ValueError("Invalid center orientation parity")
    chunks = []
    while paths[target] is not None:
        previous, moves = paths[target]
        delta = tuple((a-b) % 4 for a, b in zip(target, previous))
        chunks.append((delta, moves))
        target = previous
    return tuple(reversed(chunks))


@lru_cache(maxsize=2048)
def _center_solution(twists):
    return tuple(_compact_moves(move for _, chunk in _center_chunks(twists) for move in chunk))


def center_solution(twists):
    # Cache immutable words; callers always receive their own mutable list.
    return list(_center_solution(tuple(twists)))


def _join_centers(pieces, twists, deadline, cancelled):
    """Try orders and equivalent spellings of the selected center macros.

    Their effects commute on the fixed centers. A small beam for each subset
    keeps different formula endings, allowing cancellations at macro joins
    and at the join with the movable-piece solution. Always retain the basic
    weighted path, even if this optional search runs out of time.
    """
    chunks = _center_chunks(tuple(twists))
    centers = center_solution(twists)
    best = (tuple(_compact_moves(list(pieces) + centers)), tuple(centers))
    if not chunks:
        return best
    generators = _center_generators()
    full_mask = (1 << len(chunks)) - 1
    beams = {0: [(tuple(pieces), ())]}
    for mask in range(full_mask):
        cancelled()
        if time.perf_counter() >= deadline:
            break
        for word, suffix in beams.get(mask, ()):
            for index, (delta, _) in enumerate(chunks):
                if mask & (1 << index):
                    continue
                next_mask = mask | (1 << index)
                for macro in generators[delta]:
                    if time.perf_counter() >= deadline:
                        return best
                    joined = tuple(_compact_moves(word + macro))
                    next_suffix = suffix + macro
                    if next_mask == full_mask:
                        if len(joined) < len(best[0]):
                            best = (joined, next_suffix)
                        continue
                    beam = beams.setdefault(next_mask, [])
                    if any(existing[0] == joined for existing in beam):
                        continue
                    beam.append((joined, next_suffix))
                    beam.sort(key=lambda entry: (len(entry[0]), entry[0]))
                    del beam[4:]
    return best


def _equivalent_cubes(work, deadline, cancelled):
    """Yield legal virtual labelings with exactly the same visible geometry.

    Three-cycles of same-color wedges preserve permutation parity. Paired
    invisible twists of the small triangles can preserve corner twist sum.
    Every proposed labeling is checked against the 3x3 constraints.
    """
    from solver.solver3 import verify_3x3

    def legal(trial):
        return verify_3x3(cubies_to_facelets(trial.cubies, 3))[0]

    groups = {}
    for piece in work.cubies.values():
        if position_kind(piece.pos) == "edge":
            groups.setdefault(piece_colors(piece.home, work.palette), []).append(piece)
    for group in groups.values():
        cancelled()
        if time.perf_counter() >= deadline:
            return
        if len(group) != 3:
            continue
        options = [equivalent_placements(piece, work.palette) for piece in group]
        for shift in (1, 2):
            trial = work.clone()
            for index, piece in enumerate(group):
                home = group[(index + shift) % 3].home
                replacement = next((c for c in options[index] if c.home == home), None)
                if replacement is None:
                    break
                trial.cubies[piece.pos] = replacement
            else:
                if legal(trial):
                    yield trial
    triangles = [piece for piece in work.cubies.values()
                 if position_kind(piece.pos) == "corner"
                 and len(piece_colors(piece.home, work.palette)) == 1]
    for index, first in enumerate(triangles):
        cancelled()
        if time.perf_counter() >= deadline:
            return
        first_options = [c for c in equivalent_placements(first, work.palette)
                         if c.home == first.home and c.frame != first.frame]
        for second in triangles[index + 1:]:
            if time.perf_counter() >= deadline:
                return
            second_options = [c for c in equivalent_placements(second, work.palette)
                              if c.home == second.home and c.frame != second.frame]
            for a in first_options:
                for b in second_options:
                    trial = work.clone()
                    trial.cubies[first.pos], trial.cubies[second.pos] = a, b
                    if legal(trial):
                        yield trial


def solve_mastermorphix(cube, cancel_event=None, progress_callback=None,
                       optimization_budget=2.5):
    """Compare full solves within an additional, best-effort search budget.

    The bundled two-phase timeout is soft: a call can overrun its allowance
    while finding its first solution. Always keep the best completed result.
    This is a bounded improvement search, not a globally optimal solver.
    """
    from solver.solver3 import solve_3x3
    started = time.perf_counter()

    def cancelled():
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("cancelled")

    cancelled()
    work = normalize_input(cube)
    if work.is_solved():
        return SolveResult(True, [], "", int((time.perf_counter()-started)*1000), 0, [])
    if progress_callback:
        progress_callback({"label": "morphix.solving.pieces", "progress": .1})
    result = solve_3x3(cubies_to_facelets(work.cubies, 3))
    if not result.success:
        return result
    cancelled()
    if progress_callback:
        progress_callback({"label": "morphix.solving.centers", "progress": .5})

    def complete(piece_moves, join_deadline=None):
        trial = work.clone()
        pieces = _compact_moves(piece_moves)
        trial.apply_moves(pieces)
        twists = trial.center_twists()
        centers = center_solution(twists)
        if join_deadline is None:
            moves = _compact_moves(pieces + centers)
        else:
            moves, centers = _join_centers(pieces, twists, join_deadline, cancelled)
            moves, centers = list(moves), _compact_moves(centers)
        return moves, pieces, centers

    best = complete(result.moves)

    def retain_proposal(proposal):
        nonlocal best
        if len(proposal[0]) >= len(best[0]):
            return
        check = cube.clone()
        check.apply_moves(proposal[0])
        if check.is_solved():
            best = proposal

    deadline = time.perf_counter() + max(0., optimization_budget)
    if time.perf_counter() < deadline:
        retain_proposal(complete(result.moves, min(deadline, time.perf_counter() + .12)))

    def searches():
        yield work, (), 18
        variants = iter(_equivalent_cubes(work, deadline, cancelled))
        # Alternate geometry-equivalent labels with the existing pre-turn
        # searches so neither class consumes the entire optional budget.
        for face in "URFDLB":
            variant = next(variants, None)
            if variant is not None:
                yield variant, (), 20
            yield work, (face,), 20
        for variant in variants:
            yield variant, (), 20

    def search_key(facelets, target):
        return (target, tuple(color for face in "URFDLB"
                              for row in facelets[face] for color in row))

    solved_searches = {search_key(cubies_to_facelets(work.cubies, 3), 20): result}
    if result.moves:
        for index, (labeling, prefix, target) in enumerate(searches()):
            cancelled()
            remaining = deadline - time.perf_counter()
            if remaining <= 0 or not best[0]:
                break
            if progress_callback:
                progress_callback({"label": "morphix.solving.optimizing",
                                   "progress": min(.9, .6 + .015 * index)})
            trial = labeling.clone()
            trial.apply_moves(prefix)
            facelets = cubies_to_facelets(trial.cubies, 3)
            key = search_key(facelets, target)
            candidate = solved_searches.get(key)
            if candidate is None:
                candidate = solve_3x3(facelets, max_length=target,
                                      timeout=min(.25, remaining))
                solved_searches[key] = candidate
            cancelled()
            if not candidate.success:
                continue
            proposal = complete(list(prefix) + candidate.moves,
                                min(deadline, time.perf_counter() + .08))
            retain_proposal(proposal)

    moves, pieces, centers = best
    cancelled()
    check = cube.clone()
    check.apply_moves(moves)
    if not check.is_solved():
        raise RuntimeError("Mastermorphix shape/color verification failed")
    # Cross-stage cancellations can erase the original phase boundary.
    if moves == pieces + centers:
        stages = [SolveStage("morphix_pieces", "morphix.solving.pieces", pieces),
                  SolveStage("morphix_centers", "morphix.solving.centers", centers)]
    else:
        stages = [SolveStage("morphix_optimized", "morphix.solving.optimized", moves)]
    return SolveResult(True, moves, "", int((time.perf_counter()-started)*1000), len(moves),
                       stages)
