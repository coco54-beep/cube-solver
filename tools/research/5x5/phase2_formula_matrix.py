"""Gate 5b Phase 2 · 来源公式在 6 个翻转 fixture 上的效果分类矩阵。

对每条有来源公式 × 变体 × fixture：
  重放 fixture 得到「目标 A 已装配翻转」状态
  → normalize（纯外层）把 A 整体搬到 UF、缓冲 B 搬到某缓冲槽
  → 应用 setup + 公式变体 + inverse-setup
  → classify（A 是否变 VALID / 中心 / 固定面心 / 保护组）

只做公式适配与效果分类，不接入正式 Gate 5b。输出 `FormulaOutcome` 矩阵。
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from cube.cube5 import Cube5
from cube.middle_slice import apply_physical_sequence
from solver.edge5.flip_layout import normalize_flip_transfer
from solver.edge5.positions import MIDDLE_INDEX, slot
from solver.edge5.flip_transfer import choose_unpaired_buffer_edge
from solver.edge5.compact_state import _SLOT_MID
from solver.edge5.formula_application import (
    FormulaOutcome,
    build_variants,
    classify_formula,
    parse_sourced_sequence,
    apply_sourced_sequence,
    find_gathered_tredge_slot,
)
from solver.edge5.sourced_formulas import SOURCED_L2E

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "tests", "fixtures", "edge5", "gate5b"
)


def replay_fixture(path):
    with open(path, encoding="utf-8") as f:
        fx = json.load(f)
    c = Cube5.solved()
    for k in ("scramble", "center_moves", "gate3_moves", "gate4_moves",
              "setup_moves", "insert_moves"):
        c.apply_moves(fx[k])
    return fx, c


def apply_mixed(cube, seq):
    """应用一条可能含物理切片/3Rw 的内部动作序列（已由 parse 展开）。"""
    apply_sourced_sequence(cube, seq)


def run_matrix(max_variants_per_formula=None):
    rows = []
    for path in sorted(glob.glob(os.path.join(FIXTURE_DIR, "*.json"))):
        fx, cube = replay_fixture(path)
        fid = os.path.basename(path)
        mid_id = fx["middle_piece_id"]
        wa_id = fx["wing_a_piece_id"]
        wb_id = fx["wing_b_piece_id"]
        target_ids = (mid_id, wa_id, wb_id)
        gathered0 = find_gathered_tredge_slot(cube, target_ids)
        from solver.edge5.flip_transfer import choose_unpaired_buffer_edge
        buf = choose_unpaired_buffer_edge(cube, target_a_slot=gathered0, protected_slots=())

        for sf in SOURCED_L2E:
            parsed = parse_sourced_sequence(sf.original_formula)
            if parsed is None:
                rows.append((fid, sf.name, "原式", FormulaOutcome.NOTATION_UNSUPPORTED.name,
                             str(gathered0), "-", "none"))
                continue
            for variant in build_variants(parsed):
                if max_variants_per_formula and variant.label not in ("原式", "逆式"):
                    continue
                if buf is None or gathered0 is None:
                    rows.append((fid, sf.name, variant.label, FormulaOutcome.INVALID_STATE.name,
                                 str(gathered0), "-", "no-buffer"))
                    continue
                norm = normalize_flip_transfer(
                    cube,
                    target_middle_home=mid_id, target_wing_a_home=wa_id,
                    target_wing_b_home=wb_id, buffer_middle_home=_SLOT_MID[buf],
                )
                if not norm.success:
                    rows.append((fid, sf.name, variant.label, FormulaOutcome.INVALID_STATE.name,
                                 str(gathered0), "-", norm.error_code))
                    continue
                w = cube.clone()
                for mv in norm.setup_moves:
                    w.apply_move(mv)
                apply_sourced_sequence(w, variant.internal_seq)
                for mv in reversed(norm.setup_moves):
                    w.apply_move(_inv(mv))
                outcome = classify_formula(
                    w, target_piece_ids=target_ids, protected_slots=("UR", "UB")
                )
                a_slot_after = find_gathered_tredge_slot(w, target_ids)
                rows.append((fid, sf.name, variant.label, outcome.name,
                             str(gathered0), str(a_slot_after), "ok"))
    return rows


def _inv(mv):
    if mv.endswith("2"):
        return mv
    if mv.endswith("'"):
        return mv[:-1]
    return mv + "'"


def main():
    rows = run_matrix()
    from collections import Counter
    by_formula = {}
    for r in rows:
        by_formula.setdefault(r[1], Counter())[r[3]] += 1
    print("=== 每条公式 × 6 fixtures 的 outcome 分布 ===")
    for name, cnt in by_formula.items():
        print(f"{name[:38]:<38} {dict(cnt)}")
    print()
    total = Counter(r[3] for r in rows)
    print("=== 全部 outcome 汇总 ===")
    print(dict(total))
    print("\n=== 明细（原式 只有） ===")
    for r in rows:
        if r[2] == "原式":
            print(f"{r[0]:<16}{r[1][:36]:<36}{r[3]:<20}{r[4]:<5}->{r[5]:<6}{r[6]}")


if __name__ == "__main__":
    main()
