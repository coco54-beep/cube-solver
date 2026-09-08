"""整段物理层动作化简器（simplify_moves）回归。

验证 `solver/reduction/ref5/simplify_moves.simplify_moves`：
- 对任意外层/宽二层/切片混合动作串，化简前后在 5x5 上重放等价；
- 折叠连续同轴动作（含中间同轴段整体抵消后两侧合并的级联情形）；
- 幂等。
"""
import random

from cube.cube5 import Cube5
from solver.reduction.ref5.simplify_moves import simplify_moves

POOL = ["R", "R'", "R2", "L", "L'", "L2", "U", "U'", "U2", "D", "D'", "D2",
        "F", "F'", "F2", "B", "B'", "B2",
        "2R", "2R'", "2R2", "2L", "2L'", "2L2", "2U", "2U'", "2U2",
        "2D", "2D'", "2D2", "2F", "2F'", "2F2", "2B", "2B'", "2B2",
        "M", "M'", "M2", "E", "E'", "E2", "S", "S'", "S2",
        "u", "u'", "d", "d'", "r", "r'", "l", "l'"]


def _state_after(moves):
    c = Cube5.solved()
    c.apply_moves(list(moves))
    return {p: (cu.home, cu.stickers) for p, cu in c.cubies.items()}


def _assert_equivalent(raw, simplified):
    assert _state_after(raw) == _state_after(simplified), \
        f"化简前后不等价: {raw} -> {simplified}"


def test_basic_cancellations():
    assert simplify_moves(["R", "R"]) == ["R2"]
    assert simplify_moves(["R", "R'"]) == []
    assert simplify_moves(["R", "R2", "R"]) == []
    assert simplify_moves(["R", "2R", "R'"]) == ["2R"]
    assert simplify_moves(["M", "M'"]) == []
    assert simplify_moves(["2U", "2U"]) == ["2U2"]


def test_same_axis_commutes_across_faces():
    assert simplify_moves(["R", "L", "R'"]) == ["L"]
    assert simplify_moves(["R", "M", "R'"]) == ["M"]


def test_cascading_cancellation():
    # 中间 U 段抵消后，两侧 R 段合并再抵消。
    assert simplify_moves(["R", "U", "U'", "R'"]) == []
    assert simplify_moves(["R", "U", "U'", "R", "R'"]) == ["R"]


def test_idempotent():
    rng = random.Random(7)
    for _ in range(50):
        seq = [rng.choice(POOL) for _ in range(rng.randint(1, 60))]
        once = simplify_moves(seq)
        assert simplify_moves(once) == once


def test_random_equivalence():
    rng = random.Random(12345)
    for _ in range(200):
        seq = [rng.choice(POOL) for _ in range(rng.randint(1, 60))]
        _assert_equivalent(seq, simplify_moves(seq))


def test_unknown_tokens_are_barriers():
    # x/y/z 整体转动不参与折叠，但等价性必须保持。
    seq = ["R", "x", "R'", "U", "U'"]
    out = simplify_moves(seq)
    _assert_equivalent(seq, out)
    assert "x" in out
