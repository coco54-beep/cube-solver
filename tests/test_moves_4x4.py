"""4x4 转动引擎测试（含宽层转动）。"""

from cube.cube4 import Cube4
from tests.conftest import inverse_scramble, random_scramble
from tests.test_moves_3x3 import diff_cubes


class TestSolvedState:
    def test_is_solved(self, solved_4x4):
        assert solved_4x4.is_solved()

    def test_piece_counts(self, solved_4x4):
        types = [c.piece_type for c in solved_4x4.cubies.values()]
        assert len(types) == 56
        assert types.count("corner") == 8
        assert types.count("edge") == 24
        assert types.count("center") == 24


class TestBasicMoves:
    def test_outer_R_changes_16_cubies(self, solved_4x4):
        before = solved_4x4.clone()
        solved_4x4.apply_move("R")
        assert diff_cubes(before, solved_4x4) == 16

    def test_wide_r_changes_28_cubies(self, solved_4x4):
        before = solved_4x4.clone()
        solved_4x4.apply_move("r")
        assert diff_cubes(before, solved_4x4) == 28

    def test_R2_R2_restores(self, solved_4x4):
        before = solved_4x4.clone()
        solved_4x4.apply_moves(["R2", "R2"])
        assert solved_4x4.is_solved()
        assert diff_cubes(before, solved_4x4) == 0

    def test_narrow_scramble_then_inverse_restores(self, solved_4x4, rng):
        moves = random_scramble(rng, 4, wide=False, length=30)
        before = solved_4x4.clone()
        solved_4x4.apply_moves(moves)
        assert not solved_4x4.is_solved()
        solved_4x4.apply_moves(inverse_scramble(moves))
        assert solved_4x4.is_solved()
        assert diff_cubes(before, solved_4x4) == 0

    def test_wide_scramble_then_inverse_restores(self, solved_4x4, rng):
        moves = random_scramble(rng, 4, wide=True, length=30)
        before = solved_4x4.clone()
        solved_4x4.apply_moves(moves)
        assert not solved_4x4.is_solved()
        solved_4x4.apply_moves(inverse_scramble(moves))
        assert solved_4x4.is_solved()
        assert diff_cubes(before, solved_4x4) == 0


class TestWholeCube:
    def test_x_then_xprime_restores(self, solved_4x4):
        before = solved_4x4.clone()
        solved_4x4.apply_moves(["x", "x'"])
        assert solved_4x4.is_solved()
        assert diff_cubes(before, solved_4x4) == 0
