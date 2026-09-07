"""Gate 5b Phase 2 · 来源公式（物理 3Rw / M 解析）在 6 个翻转 fixture 上的效果分类。

Phase 1 已补齐物理中央切片（`apply_inner_slice` / `is_fixed_face_center`），
Phase 2 建立 `formula_application` 的物理解析与效果分类，并把 speedcubedb 实际
含 `3Rw` / `M` 的公式登记到 `sourced_formulas`。本测试把 **Phase 2 结论** 固化为
可复现断言：

1. 每条可用物理记号解析的来源公式在 solved cube 上重放后，**保持中心归面 +
   固定面心**（`3Rw == 2R + M` 物理分解合法）；
2. 作用于单条翻转 tredge（6 个 fixture）后，**没有任何一条公式变体达成
   Gate 5b 的 `TARGET_VALID` 契约**；结果全部表现为双棱翼交换的副作用
   （`PROTECTED_BROKEN` / `CENTER_BROKEN` / `NOTATION_UNSUPPORTED`）。

**结论**：公开 5x5 L2E 算法是**双棱翼交换**，不能单独修复单条已装配翻转 tredge；
故转向 reference-solver oracle（Phase 4），或在无法提取局部宏时把翻转缺陷
延迟至 Gate 7 联合处理。这不是「单棱翻转数学上不可解」。
"""
import json
import os

import pytest

from cube.cube5 import Cube5
from solver.edge5.sourced_formulas import SOURCED_L2E
from solver.edge5.state import is_edge_paired, centers_are_color_solved
from solver.edge5.free_slice import _fixed_centers_preserved
from solver.edge5.flip_transfer import choose_unpaired_buffer_edge
from solver.edge5.flip_layout import normalize_flip_transfer
from solver.edge5.compact_state import _SLOT_MID
from solver.edge5.formula_application import (
    FormulaOutcome,
    build_variants,
    classify_formula,
    find_gathered_tredge_slot,
    parse_sourced_sequence,
    apply_sourced_sequence,
)

GATE5B_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5b")
FIXTURES = ["flip_seed7.json", "flip_seed19.json", "flip_seed23.json",
            "flip_seed2.json", "flip_seed4.json", "flip_seed51.json"]


def _reconstruct(fx):
    c = Cube5.solved()
    for k in ("scramble", "center_moves", "gate3_moves", "gate4_moves", "setup_moves", "insert_moves"):
        c.apply_moves(fx[k])
    return c


def _physical_formulas():
    """仅返回能用物理记号解析的来源公式。"""
    return [sf for sf in SOURCED_L2E if parse_sourced_sequence(sf.original_formula) is not None]


def _inv(mv):
    if mv.endswith("2"):
        return mv
    if mv.endswith("'"):
        return mv[:-1]
    return mv + "'"


@pytest.mark.parametrize("sf", _physical_formulas(), ids=lambda sf: sf.name)
def test_physical_formula_keeps_centers_and_fixed_on_solved(sf):
    """物理解析后的来源公式在 solved 上必须保持中心归面 + 固定面心。

    `3Rw == 2R + M` 物理分解是合法的：六个固定面心不被搬走。
    """
    seq = parse_sourced_sequence(sf.original_formula)
    c = Cube5.solved()
    apply_sourced_sequence(c, seq)
    assert centers_are_color_solved(c), f"{sf.name} 破坏中心"
    assert _fixed_centers_preserved(c), f"{sf.name} 移动固定面心"


@pytest.mark.parametrize("fx_name", FIXTURES)
def test_no_physical_formula_reaches_target_valid(fx_name):
    """实证结论文档：任何可物理解析的来源公式变体都无法让单条翻转 tredge 变 VALID。

    分类结果应为 `PROTECTED_BROKEN` / `CENTER_BROKEN` / `TARGET_SCATTERED` /
    `TARGET_STILL_FLIPPED` 之一（双棱翼交换副作用），而不应为 `TARGET_VALID`。
    据此转向 oracle 或延迟至 Gate 7。
    """
    with open(os.path.join(GATE5B_DIR, fx_name), encoding="utf-8") as f:
        fx = json.load(f)
    cube = _reconstruct(fx)
    tm, ta, tb = fx["middle_piece_id"], fx["wing_a_piece_id"], fx["wing_b_piece_id"]
    target_ids = (tm, ta, tb)
    gathered0 = find_gathered_tredge_slot(cube, target_ids)
    buf = choose_unpaired_buffer_edge(cube, target_a_slot=gathered0, protected_slots=())
    assert buf is not None and gathered0 is not None

    for sf in _physical_formulas():
        parsed = parse_sourced_sequence(sf.original_formula)
        for variant in build_variants(parsed):
            norm = normalize_flip_transfer(
                cube, target_middle_home=tm, target_wing_a_home=ta,
                target_wing_b_home=tb, buffer_middle_home=_SLOT_MID[buf],
            )
            assert norm.success
            w = cube.clone()
            for mv in norm.setup_moves:
                w.apply_move(mv)
            apply_sourced_sequence(w, variant.internal_seq)
            for mv in reversed(norm.setup_moves):
                w.apply_move(_inv(mv))
            outcome = classify_formula(w, target_piece_ids=target_ids,
                                       protected_slots=("UR", "UB"))
            assert outcome != FormulaOutcome.TARGET_VALID, \
                f"{sf.name}[{variant.label}] 意外让 {fx_name} 目标变有效"
