import random
from collections import Counter

import pytest

from cube.mastermorphix import (MastermorphixCube, equivalent_placements,
                                piece_colors, position_kind, positions_for_order,
                                piece_geometry, cut_boundaries, placements, dot, NORMALS)
from cube.scramble import random_scramble
from solver.mastermorphix import solve_mastermorphix


def test_two_order_mastermorphix_input_shapes_and_solve_replay():
    solved = MastermorphixCube.solved(n=2)
    assert len(solved.positions) == 8
    assert all(position_kind(pos) == "corner" for pos in solved.positions)

    color_counts = sorted(len(piece_colors(pos, solved.palette, 2))
                          for pos in solved.positions)
    assert color_counts == [1, 1, 1, 1, 3, 3, 3, 3]

    for seed in range(3):
        cube = MastermorphixCube.solved(n=2)
        cube.apply_moves(random_scramble(2, random.Random(seed), "mastermorphix"))

        result = solve_mastermorphix(cube)

        assert result.success, result.message
        cube.apply_moves(result.moves)
        assert cube.is_solved()


def test_three_order_mastermorphix_keeps_existing_solver_path():
    cube = MastermorphixCube.solved(n=3)
    cube.apply_moves(random_scramble(3, random.Random(3), "mastermorphix"))

    result = solve_mastermorphix(cube)

    assert result.success, result.message
    cube.apply_moves(result.moves)
    assert cube.is_solved()


def test_four_order_mastermorphix_scramble_preserves_piece_identity():
    cube = MastermorphixCube.solved(n=4)
    cube.apply_moves(random_scramble(4, random.Random(0), "mastermorphix"))

    for piece in cube.cubies.values():
        matches = equivalent_placements(piece, cube.palette, 4)
        assert any(match.home == piece.home for match in matches)

    result = solve_mastermorphix(cube)

    assert result.success, result.message
    cube.apply_moves(result.moves)
    assert cube.is_solved()


def test_five_order_mastermorphix_keeps_fixed_centers_and_replays_shape():
    cube = MastermorphixCube.solved(n=5)
    cube.apply_moves(random_scramble(5, random.Random(0), "mastermorphix"))

    for piece in cube.cubies.values():
        matches = equivalent_placements(piece, cube.palette, 5)
        assert any(match.home == piece.home for match in matches)

    result = solve_mastermorphix(cube)

    assert result.success, result.message
    cube.apply_moves(result.moves)
    assert cube.is_solved()


def test_six_through_nine_order_mastermorphix_solve_random_scrambles():
    for order in range(6, 10):
        cube = MastermorphixCube.solved(n=order)
        cube.apply_moves(random_scramble(order, random.Random(2026 + order),
                                         "mastermorphix"))

        result = solve_mastermorphix(cube)

        assert result.success, (order, result.message)
        cube.apply_moves(result.moves)
        assert cube.is_solved(), order


@pytest.mark.parametrize("order", range(4, 10))
def test_high_order_curved_pieces_have_complete_colors_and_flat_cuts(order):
    positions = positions_for_order(order)
    assert len(positions) == 6*order*order - 12*order + 8
    boundaries = cut_boundaries(order)
    assert all(abs(a+b) < 1e-9 for a, b in zip(boundaries, reversed(boundaries)))
    vals = sorted({p[0] for p in positions})
    corner_colors = Counter()
    for home in positions:
        geometry = piece_geometry(home, order)
        exterior = [(points, color) for points, color in geometry if color >= 0]
        assert exterior, (order, home)
        if position_kind(home) == "corner":
            corner_colors[len(piece_colors(home, n=order))] += 1
        for points, color in geometry:
            for axis, coord in enumerate(home):
                index = vals.index(coord)
                lo, hi = boundaries[index:index+2]
                assert all(lo-1e-7 <= p[axis] <= hi+1e-7 for p in points)
            if color < 0:
                # Caps stay on mechanism planes after curving the exterior.
                assert any(all(abs(p[axis]-bound) < 1e-7 for p in points)
                           for axis in range(3) for bound in boundaries)
            else:
                # Colored facets never straddle a color seam.
                assert all(dot(NORMALS[color], p) >= max(dot(normal, p) for normal in NORMALS)-1e-7
                           for p in points)
    assert corner_colors == {1: 4, 3: 4}


@pytest.mark.parametrize("order", range(4, 10))
def test_high_order_gallery_slots_have_compatible_orbits(order):
    for pos in positions_for_order(order):
        compatible = [home for home in positions_for_order(order)
                      if position_kind(home) == position_kind(pos) and placements(home, pos)]
        assert pos in compatible
        assert len(compatible) in (6, 8, 12, 24)
