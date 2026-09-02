"""3x3 转动引擎测试。"""

from cube.cube3 import Cube3
from tests.conftest import inverse_scramble, random_scramble


def diff_cubes(a, b):
    """按 home 对齐，统计 pos 或 stickers 发生变化的块数。"""
    home_a = {c.home: c for c in a.cubies.values()}
    home_b = {c.home: c for c in b.cubies.values()}
    assert set(home_a) == set(home_b)
    return sum(
        1
        for h, c in home_a.items()
        if home_b[h].pos != c.pos or home_b[h].stickers != c.stickers
    )


class TestSolvedState:
    def test_is_solved(self, solved_3x3):
        assert solved_3x3.is_solved()

    def test_piece_counts(self, solved_3x3):
        types = [c.piece_type for c in solved_3x3.cubies.values()]
        assert len(types) == 26
        assert types.count("corner") == 8
        assert types.count("edge") == 12
        assert types.count("center") == 6


class TestBasicMoves:
    def test_single_R_changes_8_cubies(self, solved_3x3):
        before = solved_3x3.clone()
        solved_3x3.apply_move("R")
        assert diff_cubes(before, solved_3x3) == 8

    def test_R_plus_Rprime_restores(self, solved_3x3):
        before = solved_3x3.clone()
        solved_3x3.apply_moves(["R", "R'"])
        assert solved_3x3.is_solved()
        assert diff_cubes(before, solved_3x3) == 0

    def test_R2_R2_restores(self, solved_3x3):
        before = solved_3x3.clone()
        solved_3x3.apply_moves(["R2", "R2"])
        assert solved_3x3.is_solved()
        assert diff_cubes(before, solved_3x3) == 0

    def test_scramble_then_inverse_restores(self, solved_3x3, scramble_3x3_moves):
        before = solved_3x3.clone()
        solved_3x3.apply_moves(scramble_3x3_moves)
        assert not solved_3x3.is_solved()
        solved_3x3.apply_moves(inverse_scramble(scramble_3x3_moves))
        assert solved_3x3.is_solved()
        assert diff_cubes(before, solved_3x3) == 0

    def test_custom_scramble_then_inverse_restores(self, solved_3x3, rng):
        moves = random_scramble(rng, 3, length=50)
        before = solved_3x3.clone()
        solved_3x3.apply_moves(moves)
        solved_3x3.apply_moves(inverse_scramble(moves))
        assert solved_3x3.is_solved()
        assert diff_cubes(before, solved_3x3) == 0


class TestWholeCube:
    def test_x_moves_u_center(self, solved_3x3):
        u_center = solved_3x3.cubie_at((0, 1, 0))
        solved_3x3.apply_move("x")
        assert solved_3x3.cubie_at((0, 1, 0)) is not u_center

    def test_x_then_xprime_restores(self, solved_3x3):
        before = solved_3x3.clone()
        solved_3x3.apply_moves(["x", "x'"])
        assert solved_3x3.is_solved()
        assert diff_cubes(before, solved_3x3) == 0

    def test_x4_restores(self, solved_3x3):
        before = solved_3x3.clone()
        solved_3x3.apply_moves(["x", "x", "x", "x"])
        assert solved_3x3.is_solved()
        assert diff_cubes(before, solved_3x3) == 0


class TestClone:
    def test_clone_independent(self, solved_3x3):
        original = solved_3x3.clone()
        solved_3x3.apply_move("R")
        assert original.is_solved()
