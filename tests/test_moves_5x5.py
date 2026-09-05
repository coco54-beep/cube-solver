"""5x5 转动引擎测试（含宽层与任意层移动）。"""

from cube.cube5 import Cube5
from tests.conftest import inverse_scramble, random_scramble
from tests.test_moves_3x3 import diff_cubes


class TestSolvedState:
    def test_is_solved(self, solved_5x5):
        assert solved_5x5.is_solved()

    def test_piece_counts(self, solved_5x5):
        types = [c.piece_type for c in solved_5x5.cubies.values()]
        assert len(types) == 98
        assert types.count("corner") == 8
        assert types.count("edge") == 36
        assert types.count("center") == 54


class TestBasicMoves:
    def test_outer_R_changes_24_cubies(self, solved_5x5):
        before = solved_5x5.clone()
        solved_5x5.apply_move("R")
        assert diff_cubes(before, solved_5x5) == 24

    def test_wide_2R_changes_40_cubies(self, solved_5x5):
        before = solved_5x5.clone()
        solved_5x5.apply_move("2R")
        assert diff_cubes(before, solved_5x5) == 40

    def test_R3_changes_56_cubies(self, solved_5x5):
        before = solved_5x5.clone()
        solved_5x5.apply_move("3R")
        assert diff_cubes(before, solved_5x5) == 56

    def test_R2_R2_restores(self, solved_5x5):
        before = solved_5x5.clone()
        solved_5x5.apply_moves(["R2", "R2"])
        assert solved_5x5.is_solved()
        assert diff_cubes(before, solved_5x5) == 0

    def test_deep_3R_x4_restores(self, solved_5x5):
        before = solved_5x5.clone()
        solved_5x5.apply_moves(["3R", "3R", "3R", "3R"])
        assert solved_5x5.is_solved()
        assert diff_cubes(before, solved_5x5) == 0

    def test_narrow_scramble_then_inverse_restores(self, solved_5x5, rng):
        moves = random_scramble(rng, 5, length=30)
        before = solved_5x5.clone()
        solved_5x5.apply_moves(moves)
        assert not solved_5x5.is_solved()
        solved_5x5.apply_moves(inverse_scramble(moves))
        assert solved_5x5.is_solved()
        assert diff_cubes(before, solved_5x5) == 0


class TestWholeCube:
    def test_x_then_xprime_restores(self, solved_5x5):
        before = solved_5x5.clone()
        solved_5x5.apply_moves(["x", "x'"])
        assert solved_5x5.is_solved()
        assert diff_cubes(before, solved_5x5) == 0
