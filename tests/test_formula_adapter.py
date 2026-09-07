"""公式适配器测试：记号规范化、内切片复合、非法移动拒绝。"""
import pytest

from cube.cube5 import Cube5
from solver.edge5.formula_adapter import (
    expand_move, expand_sequence, inner_slice, invert_sequence, build_candidates,
)
from solver.edge5.free_slice import _fixed_centers_preserved


@pytest.mark.parametrize("tok,expected", [
    ("R", ("R",)),
    ("R2", ("R2",)),
    ("R'", ("R'",)),
    ("2R", ("2R",)),
    ("r", ("2R",)),
    ("r'", ("2R'",)),
    ("Rw", ("2R",)),
    ("Rw'", ("2R'",)),
])
def test_expand_legal(tok, expected):
    assert expand_move(tok) == expected


@pytest.mark.parametrize("tok", [
    "3R", "3R'", "3R2", "3Rw", "5R", "4L", "M", "M'", "2M", "x", "y", "z",
])
def test_reject_illegal(tok):
    assert expand_move(tok) is None


def test_inner_slice_composite_preserves_fixed_centers():
    seq = inner_slice("R")
    c = Cube5.solved()
    for mv in seq:
        c.apply_move(mv)
    # 复合应是合法状态，保持固定面心。
    assert _fixed_centers_preserved(c)


def test_inner_slice_composite_matches_expected_layer_effect():
    # layer-2-only 复合 `2R + R'` 不应触动外层 L(最左) 与固定面心。
    seq = inner_slice("R")
    c = Cube5.solved()
    for mv in seq:
        c.apply_move(mv)
    # 对 5x5，仅第二层 R 侧转动：L 侧(最外层) cubie 位置不变。
    l_mid_before = _cubie_at(Cube5.solved(), (-6, 0, 0))
    l_mid_after = _cubie_at(c, (-6, 0, 0))
    assert l_mid_after.home == l_mid_before.home


def _cubie_at(cube, pos):
    return cube.cubies[pos]


def test_expand_sequence_and_inverse():
    seq = ("Rw", "U", "Rw'", "U'")
    assert expand_sequence(seq) == ("2R", "U", "2R'", "U'")
    inv = invert_sequence(("2R", "U", "2R'", "U'"))
    assert inv == ("U", "2R", "U'", "2R'")


def test_build_candidates_skips_illegal():
    good = build_candidates(("Rw", "U", "Rw'", "U'"), name="good")
    assert len(good) == 2  # 原式 + 逆式
    bad = build_candidates(("3R", "U"), name="bad")
    assert bad == ()
