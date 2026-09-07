"""Gate 5b · 来源公式登记 + 重放检验（记录实证结果）。

对每条 `sourced_formulas.SOURCED_L2E` 公式，在 6 个翻转 fixture 的**规范化布局**
（目标 A 三块整体 -> UF，缓冲 B 中棱 -> 允许缓冲槽）上真实重放，并校验：
1. 公式在 solved cube 上**保持中心归面 + 固定面心**（在合法子空间内，正测试）；
2. 公式作用于单条翻转 tredge 时是否让目标三块**聚集且有效**（Gate 5b 期望结果）。

**实证结论文档**：公开 5x5 L2E 算法是**双棱交换**操作，会拆散单条已装配的翻转 tredge
（目标翼被移往另一槽），因此不满足 Gate 5b「目标单条 FLIPPED->VALID」契约。此测试把
该结论固化为可复现断言，防止回归，并作为转向 oracle 的依据。
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
from solver.edge5.positions import SLOT_NAMES
from solver.edge5.complete_tredge import all_three_target_pieces_in_output_slot

GATE5B_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5b")
FIXTURES = ["flip_seed7.json", "flip_seed19.json", "flip_seed23.json",
            "flip_seed2.json", "flip_seed4.json", "flip_seed51.json"]


def _reconstruct(fx):
    c = Cube5.solved()
    for k in ("scramble", "center_moves", "gate3_moves", "gate4_moves", "setup_moves", "insert_moves"):
        c.apply_moves(fx[k])
    return c


def _normalize(cube, fx):
    """把目标 A 三块整体搬到 UF、选定缓冲 B 中棱搬到允许缓冲槽。返回 (norm, layout)。"""
    st_target = [cube.cubies[p] for p in _target_current(cube, fx)]
    tm, ta, tb = fx["middle_piece_id"], fx["wing_a_piece_id"], fx["wing_b_piece_id"]
    buf = choose_unpaired_buffer_edge(cube, target_a_slot=fx["output_slot"], protected_slots=())
    if buf is None:
        return None, None
    res = normalize_flip_transfer(cube, target_middle_home=tm, target_wing_a_home=ta,
                                  target_wing_b_home=tb, buffer_middle_home=_SLOT_MID[buf])
    if not res.success:
        return None, None
    norm = cube.clone()
    for mv in res.setup_moves:
        norm.apply_move(mv)
    return norm, res.layout


def _target_current(cube, fx):
    from solver.edge5.compact_state import state_of
    from solver.edge5.positions import MIDDLE_ORDER, WING_ORDER
    s = state_of(cube)
    mi = next((j for j, v in enumerate(s.middle) if v == fx["middle_piece_id"]), None)
    ai = next((j for j, v in enumerate(s.wing) if v == fx["wing_a_piece_id"]), None)
    bi = next((j for j, v in enumerate(s.wing) if v == fx["wing_b_piece_id"]), None)
    return MIDDLE_ORDER[mi], WING_ORDER[ai], WING_ORDER[bi]


def _sourced_adaptable():
    return [sf for sf in SOURCED_L2E if sf.adaptable]


@pytest.mark.parametrize("fx_name", FIXTURES)
def test_sourced_formula_preserves_centers_and_fixed_on_solved(fx_name):
    """每条可转换公式在 solved cube 上必须保持中心归面 + 固定面心（在合法子空间内）。"""
    for sf in _sourced_adaptable():
        c = Cube5.solved()
        for mv in sf.adapted_moves:
            c.apply_move(mv)
        assert centers_are_color_solved(c), f"{sf.name} 破坏中心"
        assert _fixed_centers_preserved(c), f"{sf.name} 移动固定面心"


@pytest.mark.parametrize("fx_name", FIXTURES)
@pytest.mark.parametrize("sf", _sourced_adaptable(), ids=lambda sf: sf.name)
def test_sourced_formula_on_single_flip_tredge(fx_name, sf):
    """实证：公开 L2E 公式作用于单条翻转 tredge 时，目标三块不再聚集同槽有效。

    结果宜为 `FALSE`（断言其**不满足** Gate 5b 目标有效契约），把「L2E 是双棱交换、
    拆散单条翻转 tredge」固化。
    """
    with open(os.path.join(GATE5B_DIR, fx_name), encoding="utf-8") as f:
        fx = json.load(f)
    cube = _reconstruct(fx)
    norm, layout = _normalize(cube, fx)
    if norm is None:
        pytest.skip(f"{fx_name} 无法规范化布局")
    after = norm.clone()
    for mv in sf.adapted_moves:
        after.apply_move(mv)
    tm, ta, tb = fx["middle_piece_id"], fx["wing_a_piece_id"], fx["wing_b_piece_id"]
    target_valid = any(
        all_three_target_pieces_in_output_slot(after, tm, ta, tb, sl) and is_edge_paired(after, sl)
        for sl in SLOT_NAMES
    )
    # 文档化结论：L2E 双棱交换不应让单条翻转 tredge 变为有效（实证）。
    assert target_valid is False, f"{sf.name} 意外让 {fx_name} 目标变为有效"
