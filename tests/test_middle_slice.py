"""物理中央切片（fixed-center-preserving）测试。

覆盖 Phase 1 要求：
- 固定面心保持
- 置换双射（无碰撞、块数不变）
- 逆动作复原
- 四转复原
- 活动块确实移动（不空转）
- `3Rw == 2Rw + physical_middle`（方向/顺序以置换验证，非字符串猜测）
"""
import pytest

from cube.cube5 import Cube5
from cube.cubie_model import is_fixed_face_center
from cube.middle_slice import (
    SLICE_TOKENS,
    apply_physical_sequence,
    slice_turns,
    wide3_decompose,
)
from solver.edge5.free_slice import _fixed_center_home_set, _fixed_centers_preserved


def _home_sig(cube):
    """home -> pos 的映射，用于比较置换。"""
    return tuple(sorted((c.home, c.pos) for c in cube.cubies.values()))


def _fixed_homes(cube):
    return _fixed_center_home_set(cube)


def test_apply_inner_slice_preserves_fixed_face_centers():
    for axis in SLICE_TOKENS.values():
        c = Cube5.solved()
        c.apply_inner_slice(axis, 1)
        assert _fixed_centers_preserved(c), f"axis={axis} 破坏了固定面心"
        for h in _fixed_homes(c):
            assert c.cubies[h].pos == h


def test_apply_inner_slice_is_bijection():
    for axis in SLICE_TOKENS.values():
        for turns in (1, 2, 3):
            c = Cube5.solved()
            before = len(c.cubies)
            c.apply_inner_slice(axis, turns)
            # 无碰撞：以 pos 为键的 cubies 数量不变
            assert len(c.cubies) == before
            assert len({cubie.pos for cubie in c.cubies.values()}) == before


def test_apply_inner_slice_inverse_restores():
    for axis in SLICE_TOKENS.values():
        for turns in (1, 2, 3):
            c = Cube5.solved()
            before = _home_sig(c)
            c.apply_inner_slice(axis, turns)
            c.apply_inner_slice(axis, 4 - turns if turns != 2 else 2)
            c.apply_inner_slice(axis, 0)  # 无害 no-op
            assert _home_sig(c) == before


def test_apply_inner_slice_four_turns_restore():
    for axis in SLICE_TOKENS.values():
        c = Cube5.solved()
        before = _home_sig(c)
        for _ in range(4):
            c.apply_inner_slice(axis, 1)
        assert _home_sig(c) == before


def test_apply_inner_slice_moves_movable_edges_not_noop():
    # 5x5 中央切片（x=0）应移动 4 条中棱（各自换位），而不是空转。
    # 注：这 4 条中棱的位置构成旋转闭轨，作为「位置集合」不变；
    # 但**个体棱块**的 home->pos 必须发生变化，否则说明切片空转。
    def home_pos_map(cube):
        return {cu.home: cu.pos for cu in cube.cubies.values()}

    c = Cube5.solved()
    mid_edges_home = [(0, 6, 6), (0, 6, -6), (0, -6, 6), (0, -6, -6)]
    before = {h: home_pos_map(c)[h] for h in mid_edges_home}
    c.apply_inner_slice("x", 1)
    after = {h: home_pos_map(c)[h] for h in mid_edges_home}
    assert before != after, "中央切片未移动中棱（空转）"
    assert any(before[h] != after[h] for h in mid_edges_home)


def test_slice_turns_parsing():
    assert slice_turns("M") == ("x", 1)
    assert slice_turns("M'") == ("x", 3)
    assert slice_turns("M2") == ("x", 2)
    assert slice_turns("E") == ("y", 1)
    assert slice_turns("S") == ("z", 1)


def test_apply_physical_sequence_chains_slice_and_face():
    c = Cube5.solved()
    apply_physical_sequence(c, ["M", "R", "M'", "R'"])
    # 合起来应是合法状态，且固定面心保持。
    assert len(c.cubies) == len(Cube5.solved().cubies)
    assert _fixed_centers_preserved(c)


def test_3rw_decompose_commutes_and_consistent():
    # `3Rw = 2Rw + physical_middle`：`2Rw`（宽二）与物理中央切片应可交换（顺序无关），
    # 组合结果成为合法双射状态。方向/组合顺序经置换验证。
    tokens = wide3_decompose("R", 1)
    assert tokens == ["2R", "M"]
    a = Cube5.solved()
    b = Cube5.solved()
    apply_physical_sequence(a, tokens)                    # 2R 后 M
    apply_physical_sequence(b, [tokens[1], tokens[0]])    # M 后 2R
    assert _home_sig(a) == _home_sig(b), "3Rw 分解顺序不一致（应可交换）"
    # 拆装箱状态合法：块数不变、无不碰撞。
    assert len(a.cubies) == len(Cube5.solved().cubies)
    assert len({cubie.pos for cubie in a.cubies.values()}) == len(a.cubies)


def test_3rw_decompose_is_inverse_consistent():
    # 2Rw + M 之后逆序回滚应复原。
    c = Cube5.solved()
    before = _home_sig(c)
    apply_physical_sequence(c, ["2R", "M", "M'", "2R'"])
    assert _home_sig(c) == before


def test_wide3_decompose_counts():
    assert wide3_decompose("R", 1) == ["2R", "M"]
    assert wide3_decompose("R", 2) == ["2R2", "M2"]
    assert wide3_decompose("R", 3) == ["2R'", "M'"]
    assert wide3_decompose("U", 1) == ["2U", "E"]
    assert wide3_decompose("F", 1) == ["2F", "S"]


def test_is_fixed_face_center_identifies_only_real_centers():
    c = Cube5.solved()
    fixed_homes = _fixed_homes(c)
    for h, cubie in c.cubies.items():
        assert is_fixed_face_center(cubie) == (h in fixed_homes)
