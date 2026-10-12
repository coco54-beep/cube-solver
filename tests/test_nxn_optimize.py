import random

import pytest

from cube.cube_n import CubeN
from cube.conversion import cubies_to_facelets, facelets_to_cubies
from solver import nxn_orbits as orbit
from solver.nxn_optimize import _routes, _algorithm, _cycle_key, center_atoms
from solver.solver_n import _compress, solve_nxn


@pytest.mark.parametrize('n', [6, 7])
@pytest.mark.parametrize('wings', [False, True])
def test_short_cycle_formulas_preserve_other_piece_orbits(n, wings):
    # Check real cubie effects, including setup/inverse direction and relabelled
    # axes. Matching three markers alone cannot detect disturbed other orbits.
    for positions in orbit.orbits(n, 2 if wings else 1):
        if len(positions) != 24:
            continue
        base, start = orbit.primitive(n, positions, wings, lambda: None)
        table = _routes(n, positions, base, start, lambda: None)
        assert len(table[1]) == 24*23*22//3
        targets = random.Random(20261012).sample(sorted(table[1]), 8)
        targets += [_cycle_key(start), _cycle_key((start[0], start[2], start[1]))]
        for target in targets:
            effect = orbit._effect(n, _algorithm(table, target))
            a, b, c = [positions[i] for i in target]
            same_kind = {p: q for p, (q, count) in effect.items()
                         if count == (2 if wings else 1)}
            assert same_kind == {a: b, b: c, c: a}
            assert all(count != 3 and (wings or count == 1)
                       for _, count in effect.values())


def test_same_colour_spare_resolves_two_wrong_centres():
    cube = CubeN.solved(6)
    positions = orbit.orbits(6, 1)[0]
    a = positions[0]
    b = next(p for p in positions if cube.cubies[p].stickers != cube.cubies[a].stickers
             and next(iter(cube.cubies[p].stickers.values())) !=
             next(iter(cube.cubies[a].stickers.values())))
    ca = next(iter(cube.cubies[a].stickers.values()))
    cb = next(iter(cube.cubies[b].stickers.values()))
    cube.cubies[a].stickers = {normal: cb for normal in cube.cubies[a].stickers}
    cube.cubies[b].stickers = {normal: ca for normal in cube.cubies[b].stickers}
    atoms = center_atoms(cube, positions, lambda: None)
    cube.apply_moves(_compress(orbit.expand(atoms, cube.n), cube.n))
    assert cube.is_solved()


def test_cancelled_route_build_does_not_cache_a_partial_table():
    from solver.nxn_optimize import _ROUTES
    positions = orbit.orbits(6, 1)[0]
    base, start = orbit.primitive(6, positions, False, lambda: None)
    _ROUTES.clear()
    def cancel():
        raise RuntimeError('cancelled during setup search')
    with pytest.raises(RuntimeError, match='cancelled during setup search'):
        _routes(6, positions, base, start, cancel)
    assert not _ROUTES


def test_compression_merges_axes_after_nested_cancellation():
    assert _compress(['R', 'U', 'F', "F'", "U'", "R'"], 6) == []
    rng = random.Random(20261012)
    moves = [f'{rng.randrange(1, 7)}{rng.choice("RULDFB")}{rng.choice(["", "2", chr(39)])}'
             for _ in range(200)]
    cube = CubeN.solved(6)
    other = cube.clone()
    cube.apply_moves(moves)
    other.apply_moves(_compress(moves, 6))
    assert cubies_to_facelets(cube.cubies, 6) == cubies_to_facelets(other.cubies, 6)


def test_entered_state_solves_without_home_labels_and_can_cancel():
    from scripts.audit_solvers import make_sample
    cube, _ = make_sample('cube', 7, 20261012, cover=True)
    cube = CubeN(facelets_to_cubies(cubies_to_facelets(cube.cubies, 7), 7), 7)
    result = solve_nxn(cube)
    assert result.success, result.message
    cube.apply_moves(result.moves)
    assert cube.is_solved()

    class Cancelled:
        def is_set(self):
            return True
    assert not solve_nxn(cube, cancel_event=Cancelled()).success
