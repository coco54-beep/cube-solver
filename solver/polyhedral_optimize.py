"""Bounded improvement search for polyhedral solutions.

The stabiliser-chain and reduction solvers used for the minxes are greedy: a
small perturbation near the start changes which stage words are chosen and can
cascade into many cancellations. This module exploits that instability by
re-solving perturbed states and keeping the shortest verified sequence.

It is a best-effort improvement, not an optimal solver. Every returned word is
replayed on a fresh copy of the puzzle before it is accepted, so a caller can
safely fall back to the original solution.
"""
from random import Random
from time import monotonic
from collections import OrderedDict

from cube.polyhedral import Move
from solver.polyhedral import simplify

#: Default wall-clock budget in seconds for the improvement search.
DEFAULT_OPTIMIZE_BUDGET = 6.0


def _atoms(cube):
    """Every non-identity power of every legal layer turn."""
    order = cube.geometry.spec.turn_order
    atoms = []
    seen = set()
    for move in cube.moves():
        step = cube.geometry.spec.step(move.axis)
        for power in range(1, cube.geometry.spec.order(move.axis)):
            atom = Move(move.axis, move.layer, (step * power) % order)
            if atom.amount and atom not in seen:
                seen.add(atom)
                atoms.append(atom)
    return atoms


def _apply(cube, word):
    work = cube.entered()
    for move in word:
        work.apply_move(move)
    return work


def _verify(cube, word):
    return _apply(cube, word).is_solved()


def _seed_of(solution):
    seed = 0
    for move in solution:
        seed = (seed * 131 + move.axis * 7 + move.layer * 3 + move.amount) & 0xffffffff
    return seed


def optimize_solution(cube, solution, solver, budget=DEFAULT_OPTIMIZE_BUDGET,
                      target=None, cancel=None, progress=None, seed=None):
    """Return a verified solution no longer than ``solution`` when possible.

    ``solver`` must be the raw solver for this puzzle and must accept a puzzle
    instance, returning a move sequence. It must not itself run this search.

    ``target`` is an optional length goal: the search stops as soon as a
    solution of at most that length is found, and otherwise keeps working for
    the whole ``budget``. This trades time on hard states for a tighter spread
    of solution lengths.

    """
    best = list(solution)
    if not best:
        return tuple(best)
    order = cube.geometry.spec.turn_order
    atoms = _atoms(cube)
    if not atoms:
        return tuple(best)
    proposals=[(move.axis,move) for move in atoms]
    if cube.puzzle_kind=='pentahedron':
        # Preserve the previous random proposal distribution while evaluating
        # only distinct entered states. Zero powers become suffix restarts,
        # not emitted or applied identity turns. Aliases share memoised solves.
        canonical={(m.axis,m.layer,m.amount):m for m in atoms}
        proposals=[(move.axis,canonical.get((move.axis,move.layer,
                     power*cube.geometry.spec.step(move.axis)%order)))
                   for move in cube.moves() for power in range(1,order)]
    deadline = monotonic() + max(0.0, budget)
    rng = Random(_seed_of(best) if seed is None else seed)
    memo=OrderedDict()

    def done():
        return target is not None and len(best) <= target

    def cancelled():
        if cancel is not None and cancel():
            raise InterruptedError()

    def consider(prefix):
        nonlocal best
        work = _apply(cube, prefix)
        state=bytes(work.colors)
        try:
            word=memo.get(state)
            if word is None:
                word=tuple(solver(work))
                memo[state]=word
                if len(memo)>128:
                    memo.popitem(last=False)
            else:
                memo.move_to_end(state)
        except InterruptedError:
            raise
        except Exception:
            return False
        candidate = simplify(tuple(prefix) + tuple(word), order)
        if len(candidate) < len(best) and _verify(cube, candidate):
            best = list(candidate)
            return True
        return False

    if progress is not None:
        progress(-1, -1)

    # A cheap deterministic sweep first: single-turn perturbations often expose
    # a much shorter stage decomposition. Skip it when a single solve is
    # expensive (high-order puzzles), where the budget is better spent on
    # full re-solves.
    started = monotonic()
    cancelled()
    first=proposals[0][1]
    consider((first,) if first is not None else ())
    solve_cost = monotonic() - started
    if solve_cost * len(proposals) < 0.35 * max(0.0, budget):
        for _,move in proposals[1:]:
            if done() or monotonic() >= deadline:
                return tuple(best)
            cancelled()
            consider((move,) if move is not None else ())

    # Iterated local search: keep a prefix of the current best, perturb the
    # remaining state, and re-solve the suffix. This reaches prefixes that a
    # from-scratch restart rarely samples.
    while monotonic() < deadline:
        if done():
            break
        cancelled()
        length = len(best)
        cut = rng.randrange(0, length)
        prefix = best[:cut]
        last = best[cut - 1].axis if cut else None
        options=[m for axis,m in proposals if axis!=last] or [m for _,m in proposals]
        perturb=[rng.choice(options) for _ in range(rng.choice((1,1,2,2,3,3,4,5,6)))]
        perturb=[move for move in perturb if move is not None]
        consider(prefix + perturb)
    return tuple(best)
