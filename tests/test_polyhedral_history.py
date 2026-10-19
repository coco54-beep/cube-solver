from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble, scramble_length
from solver.polyhedral import solve_polyhedral


def test_app_scramble_history_is_a_short_complete_solution():
    for kind, n in (("super_ivy", 3), ("dino_skewb", 4), ("mosaic", 4)):
        cube = PolyhedralPuzzle.solved(kind, n)
        cube.colors = [s.face for s in cube.geometry.stickers]
        word = scramble(cube, scramble_length(cube), seed=2)
        cube.scramble_history = word
        original = cube.clone()
        solution = solve_polyhedral(cube)
        replay = original.clone()
        for move in solution:
            replay.apply_move(move)
        assert replay.is_solved()
        assert len(solution) <= 40
