"""The 3x3 Mixup must interchange centre and edge pieces, not just tilt poses."""
from cube.mixup import MixupCube, _has_centre_edge_exchange
from solver.articulated import solve_articulated


def test_mixup_45_swaps_centre_and_edge_slots():
    cube = MixupCube('mixup_333')
    assert cube.is_solved()
    move = next(m for m in cube.moves() if m.layer == 1)
    cube.apply_move(move)
    assert not cube.is_solved()
    assert _has_centre_edge_exchange(cube)


def test_mixup_scramble_replays_to_solved():
    from cube.mixup import scramble_mixup
    cube = scramble_mixup('mixup_333')
    assert not cube.is_solved()
    assert _has_centre_edge_exchange(cube)
    solution = solve_articulated(cube)
    replay = cube.clone()
    replay.apply_moves(solution)
    assert replay.is_solved()
