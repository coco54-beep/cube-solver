"""Reference oracle 的末段棱降阶器（reduce5）回归。

覆盖 Plan 5–12 的落地：对 6 个 Gate 5b 翻转 fixture（配翼后 XOR=0/1 各 3 个）
执行「配翼 → （必要时奇翼宏破配对并重配以翻转 XOR）→ A* 到 all-complete」，
验证最终态满足真正降阶判据：

- 12 条 tredge 全部 complete（中棱归属 == 翼对归属）；
- 中心归面（center_color_off == 0）且固定面心不动；
- 由 `build_reduced_facelets` + `solve_3x3` 判定的虚拟 3x3 合法。

另含一条回归：所有 `_LW_ODD_MACROS` 必须在复原态保中心（防止误用非换位子形式）。

`tools/` 非 Python 包，`reduce5` 以独立脚本存在，这里用 importlib 按文件路径加载。
"""
import importlib.util
import json
import os

import pytest

from cube.cube5 import Cube5
from solver.edge5.state import center_color_off
from solver.edge5.free_slice import _fixed_centers_preserved

_REF_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "tools", "research", "5x5", "reference"))
_REDUCE5 = os.path.join(_REF_DIR, "reduce5.py")

_spec = importlib.util.spec_from_file_location("reduce5", _REDUCE5)
r5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r5)

GATE5B_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5b")

FIXTURES = ["flip_seed19.json", "flip_seed2.json", "flip_seed51.json",
            "flip_seed23.json", "flip_seed4.json", "flip_seed7.json"]


def _fixture_state(name):
    with open(os.path.join(GATE5B_DIR, name), encoding="utf-8") as f:
        fx = json.load(f)
    c = Cube5.solved()
    for key in ["scramble", "center_moves", "gate3_moves", "gate4_moves",
                "setup_moves", "insert_moves"]:
        if key in fx:
            c.apply_moves(fx[key])
    return c


@pytest.mark.parametrize("macro", r5._LW_ODD_MACROS, ids=lambda m: "".join(m))
def test_lw_odd_macros_preserve_centers(macro):
    c = Cube5.solved()
    r5.me.apply_macro(c, macro)
    assert center_color_off(c) == 0, "奇翼 parity 宏必须保中心归面"
    assert _fixed_centers_preserved(c), "奇翼 parity 宏必须保固定面心"


@pytest.mark.parametrize("name", FIXTURES)
def test_reduce_edges_reaches_valid_reduction(name):
    c = _fixture_state(name)
    moves, info = r5.reduce_edges(c)
    assert moves is not None, f"{name} 未能降阶: {info}"
    assert info["complete"], f"{name} 存在未 complete 的 tredge"
    assert info["center_off"] == 0, f"{name} 中心错位 {info['center_off']}"
    assert info["fixed"], f"{name} 固定面心被破坏"

    check = c.clone()
    r5.me.apply_macro(check, moves)
    assert all(r5.ts.is_complete_tredge(check, n) for n in r5.ts.SLOT_NAMES)
    assert center_color_off(check) == 0
    assert _fixed_centers_preserved(check)
    assert r5.virtual_3x3_legal(check), f"{name} 虚拟 3x3 不合法"
