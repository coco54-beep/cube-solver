"""4x4 校验测试：合法状态通过，结构损坏被检出。"""

from cube.conversion import cubies_to_facelets
from cube.validation import validate_4x4

from tests.conftest import clone_facelets, random_scramble


class TestLegalStates:
    def test_solved_valid(self, solved_4x4_facelets):
        assert validate_4x4(solved_4x4_facelets) == []

    def test_scrambled_valid(self, solved_4x4, rng):
        moves = random_scramble(rng, 4, wide=True, length=30)
        solved_4x4.apply_moves(moves)
        fl = cubies_to_facelets(solved_4x4.cubies, 4)
        assert validate_4x4(fl) == []


class TestCorruptions:
    def test_illegal_color_detected(self, solved_4x4_facelets):
        fl = clone_facelets(solved_4x4_facelets)
        fl["U"][0][0] = "X"
        errors = validate_4x4(fl)
        assert errors
        assert any("非法颜色" in e for e in errors)

    def test_count_imbalance_detected(self, solved_4x4_facelets):
        fl = clone_facelets(solved_4x4_facelets)
        fl["U"][1][1] = "Y"
        errors = validate_4x4(fl)
        assert errors
        assert any("应为16" in e for e in errors)
