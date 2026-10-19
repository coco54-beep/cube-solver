from cube.cuboid import CuboidCube
from cube.polyhedral_scramble import scramble
from solver.polyhedral import solve_polyhedral


def test_super_floppy_uses_the_exact_shortest_table():
    for seed in range(5):
        cube = CuboidCube.solved("cuboid_133")
        scramble(cube, 20, seed=seed)
        original = cube.clone()
        word = solve_polyhedral(cube)
        replay = original.clone()
        for move in word:
            replay.apply_move(move)
        assert replay.is_solved()
        assert len(word) <= 12
