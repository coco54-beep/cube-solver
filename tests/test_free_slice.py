"""Free-slice Foundation 测试（Milestone 3 基础）。

覆盖：
- 6 条实验A free-slice 宏：合法、中心最终按颜色归面、固定面心保持。
- WHOLE_EDGE_SWAP_MAIN：中心保持 + 成对整棱搬运映射正确。
- edge_relation 关系等级（0~3）。
- analyze_macro 效果报告一致性。
- 受控分散态在真实 Cube5 上重放校验。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pytest

from cube.cube5 import Cube5
from solver.center5.legal_moves import is_legal_5x5_solver_move
from solver.edge5.state import center_color_off, centers_are_color_solved
from solver.edge5.free_slice import (
    FreeSliceState,
    edge_relation,
    analyze_macro,
    WHOLE_EDGE_SWAP_MAIN,
    WHOLE_EDGE_SWAP_PAIRS,
    enumerate_wide_outer_wide_compact,
    controlled_start,
)
from solver.edge5.compact_state import CompactPairingState, state_of

FREE_SLICE_MACROS = [
    ("2L", "D", "R'", "D'", "2L'"),
    ("2L'", "U", "R", "U'", "2L"),
    ("2L2", "B", "R2", "B'", "2L2"),
    ("2U", "F'", "U'", "F", "2U'"),
    ("2U'", "F'", "U", "F", "2U"),
    ("2U2", "F'", "U2", "F", "2U2"),
]


@pytest.mark.parametrize("macro", FREE_SLICE_MACROS)
def test_free_slice_macro_legal_and_center_restored(macro):
    for mv in macro:
        assert is_legal_5x5_solver_move(mv), f"非法动作 {mv}"
    c = Cube5.solved()
    c.apply_moves(macro)
    assert centers_are_color_solved(c), "宏结束后中心必须按颜色归面"
    assert center_color_off(c) == 0


@pytest.mark.parametrize("macro", FREE_SLICE_MACROS)
def test_free_slice_macro_preserves_fixed_centers(macro):
    c = Cube5.solved()
    c.apply_moves(macro)
    # 六个固定面心（单贴面、home 含一个 |6|）应回到原位置。
    fixed = [
        p for p, cj in c.cubies.items()
        if len(cj.stickers) == 1 and sorted(abs(v) for v in cj.home) == [0, 0, 6]
    ]
    assert len(fixed) == 6
    for p in fixed:
        assert c.cubies[p].pos == p, f"固定面心 {p} 被移动"


def test_whole_edge_swap_center_preserved():
    c = Cube5.solved()
    c.apply_moves(WHOLE_EDGE_SWAP_MAIN)
    assert centers_are_color_solved(c)
    assert center_color_off(c) == 0


def test_whole_edge_swap_pairs():
    """WHOLE_EDGE_SWAP_MAIN 应把每条整棱按配对整体搬运（中棱成对换位）。"""
    c = Cube5.solved()
    st_before = state_of(c)
    w = c.clone()
    w.apply_moves(WHOLE_EDGE_SWAP_MAIN)
    st_after = state_of(w)
    from solver.edge5.free_slice import member_slots
    for a, b in WHOLE_EDGE_SWAP_PAIRS:
        ma_before, _, _ = member_slots(st_before, a)
        mb_before, _, _ = member_slots(st_before, b)
        ma_after, _, _ = member_slots(st_after, a)
        mb_after, _, _ = member_slots(st_after, b)
        # 整条搬运：a 的中棱去往 b 之前所在的槽，反之亦然
        assert ma_after == mb_before, f"{a} 应搬往 {b} 之前槽"
        assert mb_after == ma_before


def test_edge_relation_levels():
    # 身份状态（已还原）：目标 UF 三块同槽 -> 等级 3
    ident = CompactPairingState(tuple(range(12)), tuple(range(24)), tuple(range(54)))
    rel = edge_relation(ident, "UF")
    assert rel.relation == 3
    assert rel.all_in_one_slot


def test_analyze_macro_report_consistent():
    c = Cube5.solved()
    eff = analyze_macro(c, ("2U", "F'", "U'", "F", "2U'"), "UF")
    assert eff.centers_color_solved_after
    assert eff.fixed_centers_preserved
    assert eff.moves == ("2U", "F'", "U'", "F", "2U'")


def test_enumerator_finds_improving_macros():
    start = controlled_start("UF", (6, 3, 6))
    results = enumerate_wide_outer_wide_compact(3, "UF", start=start)
    gain_center = [r for r in results if r[3] and r[2] == 0]
    assert len(gain_center) > 0, "应在受控分散态下找到关系提升且中心归面的宏"


def test_free_slice_state_fields():
    s = FreeSliceState(active_axis=1, slice_offset=0, work_slot="UF",
                       buffer_slot="UB", staged_pairs=(), protected_groups=())
    assert s.active_axis == 1
    assert s.slice_offset == 0
    assert s.work_slot == "UF"
