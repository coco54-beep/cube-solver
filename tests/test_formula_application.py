"""Gate 5b Phase 2 · 公式适配（物理中央切片 + 来源记号解析 + 效果分类）测试。"""
import pytest

from cube.cube5 import Cube5
from solver.edge5.formula_application import (
    FormulaOutcome,
    NotationLegend,
    build_variants,
    calibrate_formula_roundtrip,
    classify_formula,
    find_gathered_tredge_slot,
    invert_internal,
    parse_sourced_sequence,
    target_is_orientation_valid,
)
from solver.edge5.state import is_edge_paired


def test_parse_3rw_equals_compose_2rw_plus_m():
    # `3Rw` == `2Rw` + `M`（物理中央切片）
    assert parse_sourced_sequence(("3Rw",)) == ("2R", "M")
    assert parse_sourced_sequence(("3Rw'",)) == ("2R'", "M'")
    assert parse_sourced_sequence(("3Rw2",)) == ("2R2", "M2")


def test_parse_wide_and_slice_and_outer():
    assert parse_sourced_sequence(("R",)) == ("R",)
    assert parse_sourced_sequence(("R2",)) == ("R2",)
    assert parse_sourced_sequence(("Rw",)) == ("2R",)
    assert parse_sourced_sequence(("Rw'",)) == ("2R'",)
    assert parse_sourced_sequence(("r",)) == ("2R",)
    assert parse_sourced_sequence(("M",)) == ("M",)
    assert parse_sourced_sequence(("E",)) == ("E",)
    assert parse_sourced_sequence(("S",)) == ("S",)


def test_parse_rejects_whole_rotation():
    # x/y/z 无法改写时整条拒绝
    assert parse_sourced_sequence(("x", "R")) is None
    assert parse_sourced_sequence(("y", "U")) is None
    assert parse_sourced_sequence(("z",)) is None


def test_parse_k4_legend_r_is_inner_slice():
    # K4 scalar legend：`r` == 内层单切片（`2R + R'`）
    parsed = parse_sourced_sequence(("r",), legend=NotationLegend.K4_SCALAR_5X5)
    assert parsed == ("2R", "R'")


def test_parsed_moves_all_physical():
    # 解析后的动作只含外层 / 两层宽转 / 物理中央切片，不含旧 `3X` slab。
    seq = parse_sourced_sequence(("Rw2", "F2", "U2", "3Rw", "M'", "R"))
    for tok in seq:
        assert tok[0] in "RLUDFB" or tok[0] in "MES" or tok[:2] in ("2R", "2L", "2U", "2D", "2F", "2B")


def test_calibrate_roundtrip_standard_l2e():
    # 已获来源公式：Rw2 F2 U2 Rw2 U2 F2 Rw2（在 solved 上往返应回 solved）。
    seq = parse_sourced_sequence(("Rw2", "F2", "U2", "Rw2", "U2", "F2", "Rw2"))
    assert calibrate_formula_roundtrip(seq)


def test_calibrate_roundtrip_3rw_inclusive():
    seq = parse_sourced_sequence(("3Rw", "F2", "U2", "3Rw2", "U2", "F2", "3Rw"))
    assert calibrate_formula_roundtrip(seq)


def test_apply_sourced_sequence_handles_3rw():
    c = Cube5.solved()
    # `3Rw` 经 parse 预分解为 `2R + M`，再用 apply_sourced_sequence 重放。
    from solver.edge5.formula_application import apply_sourced_sequence
    seq = parse_sourced_sequence(("3Rw", "F2"))
    assert seq == ("2R", "M", "F2")
    apply_sourced_sequence(c, seq)
    # 物理中央切片后固定面心保持，状态合法。
    from solver.edge5.free_slice import _fixed_centers_preserved
    assert _fixed_centers_preserved(c)
    assert len({cu.pos for cu in c.cubies.values()}) == len(c.cubies)


def test_variants_generated():
    seq = parse_sourced_sequence(("Rw", "U", "Rw'", "U'"))
    vs = build_variants(seq)
    labels = {v.label for v in vs}
    assert "原式" in labels and "逆式" in labels and "镜像" in labels
    assert "镜像+逆式" in labels


def test_invert_internal():
    assert invert_internal(("R", "U2", "M'")) == ("M", "U2", "R'")


def test_classify_target_still_flipped_on_solved_case():
    # 在 solved 上任意构造一个「配齐但非 home」并不容易；这里只验证分类器可运行。
    c = Cube5.solved()
    # 随便取一个三块 home ids（中棱 UF + 两翼）
    from solver.edge5.compact_state import _SLOT_MID, _SLOT_WINGS
    ids = (_SLOT_MID["UF"], _SLOT_WINGS["UF"][0], _SLOT_WINGS["UF"][1])
    out = classify_formula(c, target_piece_ids=ids, protected_slots=("UR", "UB"))
    # solved 上 UF 三块（至少色对一致）应配对，故 find 应在 UF。
    assert find_gathered_tredge_slot(c, ids) == "UF"
    assert target_is_orientation_valid(c, "UF")


def test_find_gathered_tredge_slot_scattered():
    c = Cube5.solved()
    from solver.edge5.compact_state import _SLOT_MID, _SLOT_WINGS
    ids = (_SLOT_MID["UF"], _SLOT_WINGS["UF"][0], _SLOT_WINGS["UF"][1])
    # 打乱后 UF 三块未必聚集
    c.apply_moves(["R", "U", "F"])
    # 不报错即可；返回 None 或 某个槽
    find_gathered_tredge_slot(c, ids)
