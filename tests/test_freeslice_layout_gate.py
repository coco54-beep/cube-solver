"""确定性 free-slice 第二阶段 Gate 2 回归测试：固定工作布局 + 纯外层定位表。

Gate 2 要求：为 free-slice 选一套**固定**工作布局，并离线预计算「纯外层（仅 1X）
定位表」，把任意目标中棱送入工作槽、任意目标翼送入有限入口集合，且——
① 只用物理合法动作（纯外层 1X；绝不出现 3X/4X/5X）
② 若起始中心归面，则 setup 后中心仍归面（纯外层天然满足）
③ 6 个固定面心不被移动
④ 定位目标是「把 piece 送入指定位」，而非「把中心块身份送回家」（避免误区）
⑤ 多种固定背景态下结果一致；同输入返回同 setup（确定性）
⑥ 各定位序列在真实 Cube5 上重放一致。
"""

import pytest

from cube.cube5 import Cube5
from solver.edge5.compact_state import state_of
from solver.edge5.free_slice import _fixed_centers_preserved
from solver.edge5.freeslice_layout import build_layout, OUTER_MOVES
from solver.edge5.positions import MIDDLE_ORDER, WING_ORDER, MIDDLE_INDEX, WING_INDEX, slot
from solver.edge5.state import centers_are_color_solved
from solver.edge5.slice_band import band_for_open

# 固定面心集合（6 个单贴面 cubie）
def _fixed_home_set(cube):
    return {p for p, c in cube.cubies.items()
            if len(c.stickers) == 1 and sorted(abs(v) for v in c.home) == [0, 0, 6]}


def _fixed_preserved(cube):
    fixed = _fixed_home_set(cube)
    return all(cube.cubies[p].pos == p for p in fixed)


def _center_solved_random_cube(seed, depth=6):
    import random
    from solver.center5 import solve_centers5
    rnd = random.Random(seed)
    pool = ["R", "L", "U", "D", "F", "B", "R'", "L'", "U'", "D'", "F'", "B'",
            "R2", "L2", "U2", "D2", "F2", "B2", "2R", "2L", "2U", "2D", "2F", "2B",
            "2R'", "2L'", "2U'", "2D'", "2F'", "2B'"]
    c = Cube5.solved()
    c.apply_moves([rnd.choice(pool) for _ in range(depth)])
    if not centers_are_color_solved(c):
        cr = solve_centers5(c)
        c.apply_moves(cr.moves)
    assert centers_are_color_solved(c)
    return c


LAYOUT = build_layout()
WORK_MID_POS = MIDDLE_INDEX[slot(LAYOUT.work_slot).middle]
ENTRY_WING_POS = WING_INDEX[slot(LAYOUT.wing_entry_slots[0]).right_wing]


def test_layout_is_fully_defined():
    assert LAYOUT.work_slot == "UF"
    assert LAYOUT.open_move == "2U"
    assert LAYOUT.close_move == "2U'"
    assert LAYOUT.wing_entry_slots == ("UR",)
    assert set(LAYOUT.storage_slots) == set(band_for_open("2U").safe_storage_slots)
    assert LAYOUT.safe_storage_mask == band_for_open("2U").slot_mask_safe
    assert LAYOUT.touched_slots_mask == band_for_open("2U").slot_mask_touched


def test_all_middle_positions_have_setup():
    for i in range(len(MIDDLE_ORDER)):
        assert i in LAYOUT.middle_to_work, f"中棱位 {i} 无纯外层 setup"


def test_all_wing_positions_have_setup():
    for i in range(len(WING_ORDER)):
        assert i in LAYOUT.wing_to_entry, f"翼位 {i} 无纯外层 setup"


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_middle_setup_moves_piece_to_work(seed):
    """把位于各中棱位的 piece 用纯外层 setup 送入工作槽，且中心/固定面心保持。"""
    c = _center_solved_random_cube(seed)
    st0 = state_of(c)
    for i, seq in LAYOUT.middle_to_work.items():
        for m in seq:
            assert m[:1] in ("R", "L", "U", "D", "F", "B"), f"非纯外层 {m}"
        home = st0.middle[i]
        w = c.clone()
        for m in seq:
            w.apply_move(m)
        st = state_of(w)
        landed = [j for j, v in enumerate(st.middle) if v == home]
        assert landed and landed[0] == WORK_MID_POS, \
            f"seed{seed} mid i={i} 未进入工作槽: seq={seq} landed={landed}"
        assert centers_are_color_solved(w)
        assert _fixed_preserved(w)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_wing_setup_moves_piece_to_entry(seed):
    """把位于各翼位的 piece 用纯外层 setup 送入入口槽，且中心/固定面心保持。"""
    c = _center_solved_random_cube(seed)
    st0 = state_of(c)
    for i, seq in LAYOUT.wing_to_entry.items():
        for m in seq:
            assert m[:1] in ("R", "L", "U", "D", "F", "B"), f"非纯外层 {m}"
        home = st0.wing[i]
        w = c.clone()
        for m in seq:
            w.apply_move(m)
        st = state_of(w)
        landed = [j for j, v in enumerate(st.wing) if v == home]
        assert landed and landed[0] == ENTRY_WING_POS, \
            f"seed{seed} wing i={i} 未进入入口: seq={seq} landed={landed}"
        assert centers_are_color_solved(w)
        assert _fixed_preserved(w)


def test_setup_is_deterministic():
    """同输入重复构建返回完全相同的定位表（位置->序列 逐一相等）。"""
    a = build_layout()
    b = build_layout()
    assert a.middle_to_work == b.middle_to_work
    assert a.wing_to_entry == b.wing_to_entry


def _invert(mv):
    if mv.endswith("2"):
        return mv
    if mv.endswith("'"):
        return mv[:-1]
    return mv + "'"


def test_setup_sequences_are_replay_consistent():
    """定位表在原式与逆式下都一致可用（逆式即把 piece 送回原位）。"""
    for i, seq in LAYOUT.middle_to_work.items():
        inv = tuple(_invert(m) for m in reversed(seq))
        # 逆式把 piece 从工作槽送回原槽（在受控态下验证为空序列效果）
        assert all(m[:1] in ("R", "L", "U", "D", "F", "B") for m in inv)
        c = _center_solved_random_cube(11)
        st0 = state_of(c)
        home = st0.middle[i]
        w = c.clone()
        for m in seq:
            w.apply_move(m)
        assert state_of(w).middle[WORK_MID_POS] == home
        for m in inv:
            w.apply_move(m)
        # 逆式应把 piece 放回原位置
        assert state_of(w).middle[i] == home
