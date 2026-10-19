from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble, scramble_length
from solver.polyhedral import piece_orbits, solve_polyhedral


def test_super_ivy_geometry_and_orbits():
    cube = PolyhedralPuzzle("super_ivy", 3)
    geometry = cube.geometry
    assert len(geometry.pieces) == 42
    assert len(geometry.stickers) == 54
    sizes = sorted(len(piece) for piece in geometry.pieces)
    assert sizes == [1] * 30 + [2] * 12
    assert sorted(len(orbit) for orbit in piece_orbits("super_ivy", 3)) == [6, 12, 12, 12]


def test_super_ivy_solves_and_replays():
    cube = PolyhedralPuzzle.solved("super_ivy", 3)
    cube.colors = [s.face for s in cube.geometry.stickers]
    scramble(cube, scramble_length(cube), seed=3)
    word = solve_polyhedral(cube)
    replay = cube.clone()
    for move in word:
        replay.apply_move(move)
    assert replay.is_solved()
    # The corrected Rex structure has 42 moving pieces, not the old 21-piece
    # substitute. Bound the constructive solution for this fixed scramble.
    assert len(word) <= 600
