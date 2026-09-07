"""确定性 free-slice 第五阶段 Gate 5 回归测试：单条三块棱完整装配。

Gate 5 目标（用户裁定）：在固定工作布局（work=UF, open=2F, 入口=UR 右翼）下，给定一个
「中棱 + 翼-A」rel>=2 部分组合（通常已存到 safe-untouched 槽）与散置的「翼-B」，把三者
装配成**完整一条三块棱**，产出：
    is_edge_paired(after, output_slot)  ∧ 三块同住 output_slot
    ∧ centers_are_color_solved(after) ∧ fixed_centers_preserved(after) ∧ replay_consistent

核心机制：
- 纯外层联合 setup（`find_partial_wing_setup`）把部分组合之中棱送入候选 `partial_slot`、
  翼-B 送入候选入口翼位；
- free-slice 本体 `2F + outer + 2F'` 把翼-B 装配进中棱所在槽；
- 若三块已同槽但未朝向一致，用中心保持宏做 flip-fix（`_flip_fix`）；
- 多目标 `completion_goal_states` 覆盖工作槽与 safe-untouched 槽，避免单一目标过窄
  （解决 seed 5 类「中棱已在安全槽」与部分不可达问题）。

已知边界（遗留，留待后续 Gate / 专项研究）：
- seed 7：本体后三块同槽但朝向翻转，单次 2F+outer(≤4)+2F' 无法翻转 → 需更长翻转算法。
- seed 11：无任何 (partial_slot, wing_entry) 目标能把三块装配到同一槽 → 需散置恢复 /
  允许受控散开再聚集的机制。

须满足：只用物理合法动作（1X + 2X）；不改写输入；确定性；失败返回规定 error_code。
"""
import json
import os
import random

import pytest

from cube.cube5 import Cube5
from solver.center5 import solve_centers5
from solver.edge5.compact_state import _SLOT_MID, _SLOT_WINGS
from solver.edge5.complete_tredge import (
    complete_tredge, completion_goal_states, find_partial_wing_setup,
    describe_partial, all_three_target_pieces_in_output_slot,
    TredgeCompletionState, PartialRelation,
    PRECONDITION_FAILED, PARTIAL_NOT_RECOVERABLE, NO_GOAL_COMPLETED,
    FLIP_FIX_UNAVAILABLE,
)
from solver.edge5.freeslice_layout import build_layout
from solver.edge5.state import centers_are_color_solved, is_edge_paired
from solver.edge5.free_slice import _fixed_centers_preserved
from solver.edge5.positions import MIDDLE_ORDER, WING_ORDER, SLOT_NAMES

LAYOUT = build_layout()
UF_MID = _SLOT_MID["UF"]; UF_WA = _SLOT_WINGS["UF"][0]; UF_WB = _SLOT_WINGS["UF"][1]
MID_HOME = MIDDLE_ORDER[UF_MID]; WA_HOME = WING_ORDER[UF_WA]; WB_HOME = WING_ORDER[UF_WB]

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5")


def _load_fixture(seed):
    path = os.path.join(FIXTURE_DIR, f"seed{seed}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _reconstruct(fx):
    c = Cube5.solved()
    c.apply_moves(fx["scramble"])
    c.apply_moves(fx["center_moves"])
    c.apply_moves(fx["gate3_moves"])
    c.apply_moves(fx["gate4_moves"])
    return c


def _stored_state(seed):
    return _reconstruct(_load_fixture(seed))


# ------------------------- 基线：成功种子 -------------------------

@pytest.mark.parametrize("seed", [3, 6, 11, 21])
def test_gate5_completes_valid_tredge(seed):
    c = _stored_state(seed)
    r = complete_tredge(c, middle_piece_id=UF_MID, wing_a_piece_id=UF_WA,
                        wing_b_piece_id=UF_WB, layout=LAYOUT)
    assert r.success, f"seed {seed} 失败: {r.error_code} {r.message}"
    assert r.output_slot is not None
    assert r.error_code is None and r.replay_consistent
    # 成功条件：三块同槽 + is_edge_paired + 中心归面 + 固定面心保持
    after = c.clone()
    for mv in r.moves:
        after.apply_move(mv)
    assert is_edge_paired(after, r.output_slot)
    assert all_three_target_pieces_in_output_slot(after, UF_MID, UF_WA, UF_WB, r.output_slot)
    assert centers_are_color_solved(after)
    assert _fixed_centers_preserved(after)
    assert r.centers_solved_after and r.fixed_centers_preserved


@pytest.mark.parametrize("seed", [3, 6, 11, 21])
def test_gate5_moves_are_physical_and_no_3x(seed):
    c = _stored_state(seed)
    r = complete_tredge(c, middle_piece_id=UF_MID, wing_a_piece_id=UF_WA,
                        wing_b_piece_id=UF_WB, layout=LAYOUT)
    assert r.success
    for mv in r.moves:
        assert mv[:1] in ("R", "L", "U", "D", "F", "B", "2"), f"非物理动作 {mv}"
        assert mv not in ("3R", "3L", "3U", "3D", "3F", "3B"), f"非法动作 {mv}"


@pytest.mark.parametrize("seed", [3, 6, 11, 21])
def test_gate5_no_input_mutation(seed):
    c = _stored_state(seed)
    fp = tuple((p, cu.home, tuple(sorted(cu.stickers.items()))) for p, cu in sorted(c.cubies.items()))
    complete_tredge(c, middle_piece_id=UF_MID, wing_a_piece_id=UF_WA,
                    wing_b_piece_id=UF_WB, layout=LAYOUT)
    assert tuple((p, cu.home, tuple(sorted(cu.stickers.items()))) for p, cu in sorted(c.cubies.items())) == fp


@pytest.mark.parametrize("seed", [3, 6, 11, 21])
def test_gate5_deterministic(seed):
    c = _stored_state(seed)
    r1 = complete_tredge(c, middle_piece_id=UF_MID, wing_a_piece_id=UF_WA,
                         wing_b_piece_id=UF_WB, layout=LAYOUT)
    r2 = complete_tredge(c, middle_piece_id=UF_MID, wing_a_piece_id=UF_WA,
                         wing_b_piece_id=UF_WB, layout=LAYOUT)
    assert r1.success and r2.success
    assert r1.moves == r2.moves
    assert r1.output_slot == r2.output_slot


# ------------------------- 快路径：已完整 -------------------------

def test_gate5_already_valid_fast_path():
    # seed 5 的存储态本身就是一条完整正确的三块棱
    c = _stored_state(5)
    st = describe_partial(c, UF_MID, UF_WA, UF_WB)
    assert st.partial_relation is PartialRelation.VALID_TREDGE
    out = st.output_slot
    r = complete_tredge(c, middle_piece_id=UF_MID, wing_a_piece_id=UF_WA,
                        wing_b_piece_id=UF_WB, layout=LAYOUT)
    assert r.success
    assert r.moves == ()
    assert r.output_slot == out
    assert is_edge_paired(c, out)


# ------------------------- 已知边界（遗留） -------------------------

@pytest.mark.parametrize("seed,reason", [(7, "flip")])
def test_gate5_known_boundary_documented(seed, reason):
    # 把遗留边界固化：目前返回规定 error_code（不静默失败、不伪造成功）。
    c = _stored_state(seed)
    r = complete_tredge(c, middle_piece_id=UF_MID, wing_a_piece_id=UF_WA,
                        wing_b_piece_id=UF_WB, layout=LAYOUT)
    assert not r.success
    assert r.error_code == FLIP_FIX_UNAVAILABLE


# ------------------------- 单位：goal 枚举 -------------------------

def test_completion_goal_states_deterministic_and_covered():
    goals = completion_goal_states(LAYOUT)
    assert len(goals) > 0
    # 覆盖工作槽 UF 与所有 safe-untouched 槽（多目标）
    partial_slots = {g.partial_slot for g in goals}
    assert "UF" in partial_slots
    for s in ("BL", "BR", "DB", "UB"):
        assert s in partial_slots
    # 每个目标都有完整 body（open + outer + close）
    for g in goals:
        assert g.body[0] == LAYOUT.open_move
        assert g.body[-1] == LAYOUT.close_move


# ------------------------- 失败路径 -------------------------

def test_gate5_precondition_centers_unsolved_rejected():
    rnd = random.Random(2)
    c = Cube5.solved()
    c.apply_moves([rnd.choice(["R", "U", "F", "R'", "U'", "F'"]) for _ in range(4)])
    if centers_are_color_solved(c):
        c.apply_move("2R")
    assert not centers_are_color_solved(c)
    r = complete_tredge(c, middle_piece_id=UF_MID, wing_a_piece_id=UF_WA,
                        wing_b_piece_id=UF_WB, layout=LAYOUT)
    assert not r.success
    assert r.error_code == PRECONDITION_FAILED


def test_gate5_requires_recoverable_partial():
    # 构造部分组合未形成（中棱与两翼均不同槽）的散置态
    got = None
    for seed in range(1, 60):
        cc = Cube5.solved()
        rnd = random.Random(seed)
        cc.apply_moves([rnd.choice(["R", "U", "F", "D", "B", "L", "R'", "U'", "F'", "D'", "B'", "L'"])
                        for _ in range(6)])
        if not centers_are_color_solved(cc):
            continue
        st = describe_partial(cc, UF_MID, UF_WA, UF_WB)
        if st.partial_relation is PartialRelation.SCATTERED:
            got = cc
            break
    if got is None:
        pytest.skip("未找到散置态")
    r = complete_tredge(got, middle_piece_id=UF_MID, wing_a_piece_id=UF_WA,
                        wing_b_piece_id=UF_WB, layout=LAYOUT)
    assert not r.success
    assert r.error_code == PARTIAL_NOT_RECOVERABLE
