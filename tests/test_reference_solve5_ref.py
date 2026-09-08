"""Reference oracle 端到端求解器（solve5_ref）回归。

覆盖 Plan 12 的完整流水线：
中心归面 → 配翼 + 末段降阶（reduce5）→ **中棱朝向修正**（middle_orient_fix）
→ 虚拟 3x3（solve_3x3）→ 回放。

关键回归点：`reduce5` 只对齐色对，会留下「中棱相对翼内部翻转」；
`middle_orient_fix` 用「中棱恒等置换 + 2-flip」宏词的 GF(2) 组合消去该偏差，
使虚拟 3x3 回放后 `cube.is_solved()` 真正成立（此前 `virtual_3x3_legal`
单判据是假阳性，见 PROGRESS.md 第 11 节）。

`tools/` 非 Python 包，模块以文件路径 + sys.path 方式加载。
"""
import importlib.util
import os
import random
import sys

import pytest

from cube.cube5 import Cube5

_REF_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "tools", "research", "5x5", "reference"))
if _REF_DIR not in sys.path:
    sys.path.insert(0, _REF_DIR)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_REF_DIR, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def solve5():
    return _load("solve5_ref")


@pytest.fixture(scope="module")
def mof():
    return _load("middle_orient_fix")


@pytest.mark.parametrize("seed", [3, 19, 42, 101])
def test_solve5_ref_end_to_end(solve5, seed):
    rng = random.Random(seed)
    c = Cube5.solved()
    solve5._random_scramble(c, 40, rng)
    moves, info = solve5.solve5_ref(c)
    assert moves is not None, f"seed {seed} 求解失败: {info}"
    check = c.clone()
    solve5.me.apply_macro(check, moves)
    assert check.is_solved(), f"seed {seed} 回放后未复原: {info}"
    assert info["solved"]


def test_middle_orient_fix_makes_consistent(solve5, mof):
    """reduce5 输出上，修正后中棱与左翼朝向必须逐槽一致。"""
    rng = random.Random(3)
    c = Cube5.solved()
    solve5._random_scramble(c, 40, rng)
    from solver.center5 import solve_centers5
    solve5.me.apply_macro(c, solve_centers5(c).moves)
    emoves, _ = solve5.r5.reduce_edges(c, iters=2000000)
    solve5.me.apply_macro(c, emoves)

    mo0, wo0 = mof.orient_bits(c)
    moves, info = mof.fix_middle_orientation(c)
    assert moves is not None, info
    check = c.clone()
    mof.me.apply_macro(check, moves)
    mo1, wo1 = mof.orient_bits(check)
    assert mo1 == wo1, f"朝向仍未一致: {mo1} vs {wo1}"
