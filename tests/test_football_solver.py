"""Tuttminx / football reduction solver: legality replay and step-count guard."""

import random

import pytest

from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import solve_polyhedral


def _scramble(n, seed, turns):
    cube = PolyhedralPuzzle.solved('football', n)
    rng = random.Random(seed)
    moves = cube.moves()
    for _ in range(turns):
        move = rng.choice(moves)
        order = cube.geometry.spec.order(move.axis)
        amount = rng.randrange(1, order)
        cube.apply_move(move.__class__(move.axis, move.layer,
                                       amount*cube.geometry.spec.step(move.axis)))
    return cube


@pytest.mark.parametrize("order,seed,turns,limit", [
    (3, 0, 20, 1500),
    (3, 1, 20, 1500),
    (5, 0, 16, 2600),
])
def test_football_solution_replays_and_stays_compact(order, seed, turns, limit):
    cube = _scramble(order, seed, turns)
    solution = solve_polyhedral(cube)

    replay = cube.entered()
    for move in solution:
        replay.apply_move(move)
    assert replay.is_solved()
    # Guards the protected-orbit macro reduction from silently regressing.
    assert len(solution) < limit
