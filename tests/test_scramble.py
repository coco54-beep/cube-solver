"""打乱公式解析 (cube/scramble.py) 的单元测试。"""

import random

import pytest

from cube.scramble import text_to_moves, random_scramble
from cube.conversion import cubies_to_facelets
from cube.notation import parse_move_full
from cube.cube2 import Cube2
from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.cube5 import Cube5
from cube.validation import validate_3x3

_LENGTH = {2: (9, 11), 3: (20, 25), 4: (40, 45), 5: (60, 70)}
_CUBES = {2: Cube2, 3: Cube3, 4: Cube4, 5: Cube5}
_AXIS = {"U": 1, "D": 1, "F": 2, "B": 2, "R": 0, "L": 0}


def _axis_of(tok):
    for ch in tok:
        if ch.isalpha() and ch.lower() in "udfbrl":
            return _AXIS[ch.upper()]
    return None


def _invert(tok):
    if tok.endswith("'"):
        return tok[:-1]
    if tok.endswith("2"):
        return tok
    return tok + "'"


def test_whitespace_and_commas():
    for text in ("R U R' U'", "R,U,R',U'", "R，U、R'；U'", "R\tU\nR'  U'"):
        moves, skipped = text_to_moves(text, 3)
        assert moves == ["R", "U", "R'", "U'"]
        assert skipped == 0


def test_scramble_prefix_and_wide_notation():
    moves, _ = text_to_moves("Scramble: Rw U2 3Rw'", 3)
    assert moves == ["r", "U2", "3r'"]

    moves, _ = text_to_moves("打乱：r u'", 4)
    assert moves == ["r", "u'"]


def test_rotations_skipped():
    moves, skipped = text_to_moves("x R U y'", 3)
    assert moves == ["R", "U"]
    assert skipped == 2

    with pytest.raises(ValueError):
        text_to_moves("x R", 3, skip_rotations=False)


def test_invalid_moves_raise_token():
    with pytest.raises(ValueError) as e:
        text_to_moves("R Q U", 3)
    assert str(e.value) == "Q"

    with pytest.raises(ValueError) as e:
        text_to_moves("R2'", 3)
    assert str(e.value) == "R2'"


def test_wide_rejected_on_2x2():
    with pytest.raises(ValueError):
        text_to_moves("Rw U", 2)


def test_apply_and_inverse_restores_solved():
    scramble = "R U R' U' F2 L D'"
    inverse = "D L' F2 U R U' R'"
    cube = Cube3.solved()
    moves, _ = text_to_moves(scramble, 3)
    cube.apply_moves(moves)
    assert not cube.is_solved()
    inv, _ = text_to_moves(inverse, 3)
    cube.apply_moves(inv)
    assert cube.is_solved()


def test_scramble_produces_valid_state():
    cube = Cube3.solved()
    moves, _ = text_to_moves("Scramble: R U2 F' L2 D B R' U'", 3)
    cube.apply_moves(moves)
    facelets = cubies_to_facelets(cube.cubies, 3)
    assert validate_3x3(facelets) == []


def test_wide_scramble_on_4x4_roundtrip():
    cube = Cube4.solved()
    moves, _ = text_to_moves("Rw U2 3Rw' F r'", 4)
    cube.apply_moves(moves)
    assert not cube.is_solved()
    inv, _ = text_to_moves("r F' 3Rw U2 Rw'", 4)
    cube.apply_moves(inv)
    assert cube.is_solved()


def test_random_scramble_length_and_no_same_axis():
    for n, (lo, hi) in _LENGTH.items():
        moves = random_scramble(n, rng=random.Random(n))
        assert lo <= len(moves) <= hi
        axes = [_axis_of(t) for t in moves]
        assert all(a is not None for a in axes)
        assert all(a != b for a, b in zip(axes, axes[1:]))


def test_random_scramble_deterministic():
    a = random_scramble(5, rng=random.Random(42))
    b = random_scramble(5, rng=random.Random(42))
    assert a == b


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_random_scramble_apply_inverse_roundtrip(n):
    moves = random_scramble(n, rng=random.Random(7))
    cube = _CUBES[n].solved()
    cube.apply_moves(moves)
    assert not cube.is_solved()
    cube.apply_moves([_invert(t) for t in reversed(moves)])
    assert cube.is_solved()


def test_random_scramble_5x5_may_use_three_layer():
    """5x5 随机打乱允许 3 层转（会移动固定面心），token 均合法且不非法叠层。"""
    saw_three = False
    for seed in range(15):
        moves = random_scramble(5, rng=random.Random(seed))
        for tok in moves:
            _, layers, _ = parse_move_full(tok)
            assert layers in (1, 2, 3), (seed, tok)
            saw_three = saw_three or layers == 3
    assert saw_three, "15 个种子中应至少出现一次 3 层转"
