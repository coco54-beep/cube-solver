"""notation 解析/标准化/逆公式测试。"""

import pytest

from cube.notation import (
    FACE_LABELS,
    WHOLE_LABELS,
    inverse_algorithm,
    inverse_move,
    moves_to_str,
    normalize_label_base,
    normalize_move,
    parse_algorithm,
    parse_move_str,
    parse_suffix,
    suffix_for_count,
)


class TestParseSuffix:
    def test_no_suffix_is_one(self):
        assert parse_suffix("") == 1

    def test_prime_is_three(self):
        assert parse_suffix("'") == 3

    def test_double_prime_is_two(self):
        assert parse_suffix("''") == 2

    def test_digit_two(self):
        assert parse_suffix("2") == 2

    def test_digit_three(self):
        assert parse_suffix("3") == 3

    def test_invalid_raises(self):
        for bad in ("4", "x", "''2", "'2", "''x"):
            with pytest.raises(ValueError):
                parse_suffix(bad)


class TestSuffixForCount:
    def test_mappings(self):
        assert suffix_for_count(1) == ""
        assert suffix_for_count(2) == "2"
        assert suffix_for_count(3) == "'"

    def test_invalid_raises(self):
        for bad in (0, 4, -1, 5):
            with pytest.raises(ValueError):
                suffix_for_count(bad)


class TestNormalizeLabelBase:
    @pytest.mark.parametrize("base", list("rludfb"))
    def test_lowercase_face_uppercases(self, base):
        assert normalize_label_base(base) == base.upper()

    @pytest.mark.parametrize("whole", list(WHOLE_LABELS))
    def test_whole_unchanged(self, whole):
        assert normalize_label_base(whole) == whole

    def test_invalid_raises(self):
        for bad in ("Q", "q", "A", "s", "w"):
            with pytest.raises(ValueError):
                normalize_label_base(bad)


class TestParseMoveStr:
    @pytest.mark.parametrize(
        "s,expected",
        [
            ("R", ("R", False, 1)),
            ("R'", ("R", False, 3)),
            ("R''", ("R", False, 2)),
            ("R2", ("R", False, 2)),
            ("R3", ("R", False, 3)),
            ("r", ("R", True, 1)),
            ("r'", ("R", True, 3)),
            ("r2", ("R", True, 2)),
            ("x", ("x", False, 1)),
            ("x'", ("x", False, 3)),
            ("x2", ("x", False, 2)),
            ("y3", ("y", False, 3)),
            ("z", ("z", False, 1)),
        ],
    )
    def test_valid(self, s, expected):
        assert parse_move_str(s) == expected

    def test_whitespace_stripped(self):
        assert parse_move_str("  R'  ") == ("R", False, 3)

    @pytest.mark.parametrize("s", ["", "Q", "R4", "R'2", "R''2", "r2'", "x''2"])
    def test_invalid_raises(self, s):
        with pytest.raises(ValueError):
            parse_move_str(s)

    def test_wide_rejected_when_not_allowed(self):
        with pytest.raises(ValueError):
            parse_move_str("r", allow_wide=False)


class TestInverseMove:
    @pytest.mark.parametrize(
        "move,expected",
        [
            (("R", False, 1), ("R", False, 3)),
            (("R", False, 2), ("R", False, 2)),
            (("R", False, 3), ("R", False, 1)),
            (("R", True, 1), ("R", True, 3)),
            (("x", False, 1), ("x", False, 3)),
        ],
    )
    def test_single(self, move, expected):
        assert inverse_move(move) == expected

    def test_involution(self):
        for label in list(FACE_LABELS) + list(WHOLE_LABELS):
            for is_wide in (False, True):
                if label in WHOLE_LABELS and is_wide:
                    continue
                for count in (1, 2, 3):
                    m = (label, is_wide, count)
                    assert inverse_move(inverse_move(m)) == m


class TestParseAlgorithm:
    def test_simple(self):
        assert parse_algorithm("R U R2") == [
            ("R", False, 1),
            ("U", False, 1),
            ("R", False, 2),
        ]

    def test_whitespace_variants(self):
        assert parse_algorithm("R\nU\tF'") == [
            ("R", False, 1),
            ("U", False, 1),
            ("F", False, 3),
        ]

    def test_empty(self):
        assert parse_algorithm("   \n\t  ") == []

    def test_wide_rejected_when_not_allowed(self):
        with pytest.raises(ValueError):
            parse_algorithm("r u", allow_wide=False)


class TestInverseAlgorithm:
    def test_order_and_inverse(self):
        moves = [("R", False, 1), ("U", False, 2), ("F", False, 3)]
        assert inverse_algorithm(moves) == [
            ("F", False, 1),
            ("U", False, 2),
            ("R", False, 3),
        ]

    def test_empty(self):
        assert inverse_algorithm([]) == []


class TestNormalizeMove:
    def test_narrow(self):
        assert normalize_move(("R", False, 1)) == "R"
        assert normalize_move(("R", False, 2)) == "R2"
        assert normalize_move(("R", False, 3)) == "R'"

    def test_wide(self):
        assert normalize_move(("R", True, 1)) == "Rw"
        assert normalize_move(("R", True, 2)) == "Rw2"
        assert normalize_move(("R", True, 3)) == "Rw'"

    def test_whole(self):
        assert normalize_move(("x", False, 1)) == "x"
        assert normalize_move(("x", False, 2)) == "x2"
        assert normalize_move(("z", False, 3)) == "z'"

    def test_wide_normalized_not_parseable_back(self):
        # normalize_move 用 "Rw" 记宽层；parse_move_str 用小写 "r"，"Rw" 不可解析
        with pytest.raises(ValueError):
            parse_move_str("Rw")


class TestMovesToStr:
    def test_joins(self):
        assert moves_to_str([("R", False, 1), ("U", False, 3)]) == "R U'"

    def test_roundtrip_narrow_and_whole(self):
        for label in list(FACE_LABELS) + list(WHOLE_LABELS):
            for count in (1, 2, 3):
                s = normalize_move((label, False, count))
                assert parse_move_str(s) == (label, False, count)
