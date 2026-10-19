import pytest

from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble, scramble_length
from solver.polyhedral import solve_polyhedral

KINDS = ("petal_tetrahedron", "petal_tetrahedron_nocentre",
         "petal_icosahedron", "petal_icosahedron_nocentre")


@pytest.mark.parametrize("kind", KINDS)
def test_petal_puzzle_scramble_solves_and_replays(kind):
    cube = PolyhedralPuzzle.solved(kind, 3)
    cube.colors = [s.face for s in cube.geometry.stickers]
    scramble(cube, scramble_length(cube), seed=5)
    word = solve_polyhedral(cube)
    replay = cube.clone()
    for move in word:
        replay.apply_move(move)
    assert replay.is_solved()
    if kind in ("petal_tetrahedron", "petal_tetrahedron_nocentre"):
        assert len(word) <= 64
    if kind == "petal_icosahedron":
        assert len(word) <= 400
