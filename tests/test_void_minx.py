from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble
from solver.polyhedral import solve_polyhedral


def test_void_minx_geometry():
    cube = PolyhedralPuzzle("void_minx", 3)
    assert len(cube.colors) == 120
    assert all(len(piece) > 1 for piece in cube.geometry.pieces)


def test_void_minx_solves_and_replays():
    cube = PolyhedralPuzzle("void_minx", 3)
    cube.colors = [s.face for s in cube.geometry.stickers]
    scramble(cube, 10, seed=1)
    solution = solve_polyhedral(cube)
    replay = cube.clone()
    for move in solution:
        replay.apply_move(move)
    assert replay.is_solved()
