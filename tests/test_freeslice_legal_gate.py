"""确定性 free-slice 第一阶段 Gate 回归测试。

Gate 要求：在受控(分散)起始态上，用**物理合法**动作（仅 1X 外层 + 2X 宽转）的一条
W + outer + W' 宏，把目标翼聚到目标中棱槽，使关系提升为 combo(2)/paired(3)，
且宏后①中心保持归面 ②6 个固定面心不被移动。

通过该 Gate 才允许继续扩展为完整确定性 free-slice；任何依赖 3X 提升配对的结果
都属非物理，禁止进入正式算法。
"""

import pytest

from cube.cube5 import Cube5
from solver.edge5.compact_state import state_of
from solver.edge5.free_slice import (
    controlled_start,
    enumerate_wide_outer_wide_compact,
    edge_relation,
)
from solver.edge5.positions import slot
from solver.edge5.state import centers_are_color_solved


def _fixed_center_home_set(cube):
    return {p for p, c in cube.cubies.items()
            if len(c.stickers) == 1 and sorted(abs(v) for v in c.home) == [0, 0, 6]}


def _fixed_preserved(cube):
    fixed = _fixed_center_home_set(cube)
    return all(cube.cubies[p].pos == p for p in fixed)


@pytest.mark.parametrize("target,entry_slot,entry_wing", [
    ("UF", "UR", "right_wing"),
    ("UF", "UR", "left_wing"),
    ("FR", "DR", "right_wing"),
    ("DL", "FL", "left_wing"),
])
def test_gate_legal_macro_gathers_wing_keeping_centers_fixed(target, entry_slot, entry_wing):
    entry_pos = getattr(slot(entry_slot), entry_wing)
    # 受控起始：目标中棱 home、目标两翼都散置到非目标槽（初始关系必须 < combo=2）
    start = controlled_start(target, entry_pos)
    rel0 = edge_relation(start, target).relation
    # 强化：初始关系必须低于目标（否则后续「提升」被翼-b 停在目标槽所掩蔽）
    assert rel0 < 2, f"受控起始关系应 <2（分散），实际 rel0={rel0}（掩蔽风险）"

    found = None
    for max_outer in (2, 3):
        found = None
        for mv, rel, co, improved in enumerate_wide_outer_wide_compact(max_outer, target, start):
            # 用物理合法枚举器保证只用 1X/2X（compact MOVES 已剔除 3X）
            if improved and rel >= 2 and co == 0:
                found = (mv, rel)
                break
        if found:
            break

    assert found is not None, "无合法 W+outer+W' 宏能把目标翼聚到中棱槽且中心归面"
    mv, rel = found

    # 全部动作必须是 1X(外层) 或 2X(宽转)——不出现 3X/4X/5X 等非物理动作。
    for m in mv:
        assert m[:1] in ("R", "L", "U", "D", "F", "B", "2"), f"出现非物理动作: {m}"

    # 真实 Cube5 重放（只含 1X/2X 合法动作）
    w = Cube5.solved()
    for m in mv:
        w.apply_move(m)

    r_after = edge_relation(state_of(w), target)
    assert r_after.relation >= 2
    # 强化：真实重放须严格提升（> 初始关系），且中心/固定面心保持。
    assert r_after.relation > rel0, "真实重放关系未严格提升"
    assert centers_are_color_solved(w)
    assert _fixed_preserved(w)
