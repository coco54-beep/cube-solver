"""Pentacle uses a verified inverse for app scrambles and macro search for short inputs."""
from cube.pentacle import PentacleCube
from cube.polyhedral import Move
from solver.pentacle import solve_pentacle


def test_pentacle_scramble_replays_to_solved():
    cube = PentacleCube()
    cube.apply_moves(cube.alignment_moves(0))
    cube.apply_move(Move(0, 1, 90))
    cube.apply_move(Move(0, 0, 36))
    solution = solve_pentacle(cube)
    replay = cube.clone()
    replay.apply_moves(solution)
    assert replay.is_solved()


def test_pentacle_macro_search_for_short_input():
    cube = PentacleCube()
    cube.apply_moves(cube.alignment_moves(0))
    cube.apply_move(Move(0, 1, 90))
    cube.history = []
    cube._history_snapshot = cube.frames
    solution = solve_pentacle(cube)
    replay = cube.clone()
    replay.apply_moves(solution)
    assert replay.is_solved()
