"""逻辑棱朝向模块 · 自我一致性验证（Gate 5b 前置）。

**重要诚实说明**：`edge_cubie_flip`（相对 home 轴指派）是**绝对**测量，不是合法移动群
的奇偶不变式，也**不等同**于「槽内相对翻转」（后者是相对于同槽两翼的测量）。已实证：
- 纯外层序列（如 `U' L L2`）可改变中棱/翼「绝对翻转」奇偶；
- 单翼翻转为非 0（与旧研究「翼永远不各自翻转」不同，因该结论指相对一致而非绝对）；
- 同一逻辑棱的绝对翻转 与 其在某槽的「中棱相对两翼翻转」可能不一致（seed51 例）。

因此本模块定位为**探测器**，在此只验证：可复现、solved 全零、12 维形态稳定。
**绝不以「当前宏观修不了 ⇒ 群论不可达」下结论。**
"""
import random

from cube.cube5 import Cube5
from solver.edge5.orientation import edge_orientation_report


def test_report_deterministic():
    rnd = random.Random(7)
    BASES = "2U 2D 2L 2R 2F 2B U D L R F B".split()
    LEGAL = (tuple(BASES) + tuple(x + "'" for x in BASES)
             + tuple(x + "2" for x in "U D L R F B".split()))
    sc = [rnd.choice(LEGAL) for _ in range(8)]
    c = Cube5.solved()
    c.apply_moves(sc)
    assert edge_orientation_report(c) == edge_orientation_report(c)
    r = edge_orientation_report(c)
    assert len(r.logical_edge_orientations) == 12
    assert len(r.flipped_edge_types) == sum(r.logical_edge_orientations)


def test_solved_report_all_zero():
    r = edge_orientation_report(Cube5.solved())
    assert all(b == 0 for b in r.logical_edge_orientations)
    assert r.middle_flip_parity == 0
    assert r.flipped_logical_slots == ()
    assert r.flipped_edge_types == ()
