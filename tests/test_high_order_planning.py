"""Exact boundary scoring against the full simplifier, without solving."""
import random

import pytest

from cube.polyhedral import Move
from solver.polyhedral import simplify
from solver.polyhedral_reduction import joined_length


@pytest.mark.parametrize('order', [3, 5, 15])
def test_joined_length_matches_full_simplification(order):
    rng = random.Random(12345)
    for _ in range(1000):
        words = []
        for _ in range(2):
            words.append(simplify(tuple(Move(rng.randrange(4), rng.randrange(6),
                                             rng.randrange(1, order))
                                        for _ in range(rng.randrange(80))), order))
        left, right = words
        assert joined_length(left, right, order) == len(simplify(left + right, order))


def test_joined_length_cascades_across_cancelled_blocks():
    left = (Move(0, 0, 1), Move(1, 2, 2), Move(2, 0, 3))
    right = (Move(2, 0, 2), Move(1, 2, 3), Move(0, 0, 4))
    assert joined_length(left, right, 5) == 0


def test_shallow_minx_reuses_probe_without_running_beam_twice(monkeypatch):
    from cube.polyhedral import PolyhedralPuzzle
    from solver import high_minx_reduction as reduction
    from solver import polyhedral_reduction as planner
    cube = PolyhedralPuzzle.solved('megaminx', 6)
    monkeypatch.setattr(planner, '_beam_probe', lambda *args: (cube.entered(), (), 0, 100))
    def duplicate_search(*args, **kwargs):
        raise AssertionError('Probe search was run twice')
    monkeypatch.setattr(reduction, 'native_beam', duplicate_search)
    monkeypatch.setattr(reduction, 'solve_orbits', lambda *args: [])
    monkeypatch.setattr(reduction, 'build_twist_gadget', lambda *args: None)
    assert planner.solve_high_minx(cube) == ()
