"""3x3 校验测试：合法状态通过，各类损坏被检出。"""

from cube.conversion import cubies_to_facelets
from cube.coordinates import rc_from_pos
from cube.validation import validate_3x3

from tests.conftest import clone_facelets, faces_of, random_scramble, swap_cells


def cell(face, pos, n=3):
    r, c = rc_from_pos(n, face, pos)
    return (face, r, c)


def do_swap(facelets, c0, c1):
    (fa, ra, ca), (fb, rb, cb) = c0, c1
    swap_cells(facelets, fa, ra, ca, fb, rb, cb)


class TestLegalStates:
    def test_solved_valid(self, solved_3x3_facelets):
        assert validate_3x3(solved_3x3_facelets) == []

    def test_scrambled_valid(self, solved_3x3, rng):
        moves = random_scramble(rng, 3, length=30)
        solved_3x3.apply_moves(moves)
        fl = cubies_to_facelets(solved_3x3.cubies, 3)
        assert validate_3x3(fl) == []


class TestCorruptions:
    def test_corner_twist_detected(self, solved_3x3_facelets):
        fl = clone_facelets(solved_3x3_facelets)
        pos = (1, 1, 1)  # R-U-F 角块
        faces = faces_of(pos)
        assert set(faces) == {"R", "U", "F"}
        do_swap(fl, cell(faces[0], pos), cell(faces[1], pos))
        errors = validate_3x3(fl)
        assert errors
        assert any("扭转" in e for e in errors)

    def test_edge_flip_detected(self, solved_3x3_facelets):
        fl = clone_facelets(solved_3x3_facelets)
        pos = (0, 1, 1)  # U-F 棱块
        faces = faces_of(pos)
        assert len(faces) == 2
        do_swap(fl, cell(faces[0], pos), cell(faces[1], pos))
        errors = validate_3x3(fl)
        assert errors
        assert any("翻转" in e for e in errors)

    def test_parity_detected(self, solved_3x3_facelets):
        fl = clone_facelets(solved_3x3_facelets)
        a = (0, 1, 1)  # U-F 棱
        b = (0, 1, -1)  # U-B 棱
        fa, fb = faces_of(a), faces_of(b)
        for f1, f2 in zip(fa, fb):
            do_swap(fl, cell(f1, a), cell(f2, b))
        errors = validate_3x3(fl)
        assert errors
        assert any("奇偶" in e for e in errors)
