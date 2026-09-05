"""5x5 校验测试：合法状态通过，结构损坏被检出。"""

from cube.conversion import cubies_to_facelets
from cube.validation import validate_5x5

from tests.conftest import clone_facelets, random_scramble


class TestLegalStates:
    def test_solved_valid(self, solved_5x5_facelets):
        assert validate_5x5(solved_5x5_facelets) == []

    def test_scrambled_valid(self, solved_5x5, rng):
        moves = random_scramble(rng, 5, length=30)
        solved_5x5.apply_moves(moves)
        fl = cubies_to_facelets(solved_5x5.cubies, 5)
        assert validate_5x5(fl) == []


class TestCorruptions:
    def test_illegal_color_detected(self, solved_5x5_facelets):
        fl = clone_facelets(solved_5x5_facelets)
        fl["U"][0][0] = "X"
        errors = validate_5x5(fl)
        assert errors
        assert any("非法颜色" in e for e in errors)

    def test_count_imbalance_detected(self, solved_5x5_facelets):
        fl = clone_facelets(solved_5x5_facelets)
        fl["U"][2][2] = "Y"
        errors = validate_5x5(fl)
        assert errors
        assert any("应为25" in e for e in errors)
