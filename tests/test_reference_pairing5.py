"""Reference oracle 的独立 5x5 配棱器（pairing5）回归。

与生产 `solver/edge5` 无关的 commutator 配棱器，验证它能：
- 在「宽转打乱」（单层转无法拆散 5x5 棱对，必须用宽转/内层）下把 12 槽两翼配齐；
- 在 Gate 5b 翻转 fixtures（深态 init 1~4/12）上配齐；
- 全程保持中心归面（center color-solved）与固定面心。

因为 `tools/` 非 Python 包，`pairing5` 以独立脚本存在，这里用 importlib 按文件路径加载。
"""
import importlib.util
import json
import os
import random

import pytest

from cube.cube5 import Cube5
from solver.edge5.state import centers_are_color_solved, center_color_off
from solver.edge5.free_slice import _fixed_centers_preserved
from solver.edge5.positions import edge_type_of_cubie

_REF_DIR = os.path.join(os.path.dirname(__file__), "..", "tools", "research", "5x5", "reference")
_REVIEW = os.path.abspath(os.path.join(_REF_DIR, "pairing5.py"))

_spec = importlib.util.spec_from_file_location("pairing5", _REVIEW)
p5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p5)

GATE5B_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5b")

WIDE = ["2R", "2R'", "2L", "2L'", "2U", "2U'", "2D", "2D'", "2F", "2F'", "2B", "2B'"]


def _matched(cube):
    """按位置所属槽统计两翼同色对的槽数（edge5 语义）。"""
    from collections import defaultdict
    wa = {p: edge_type_of_cubie(cube.cubies[p])
          for p in p5.WINGS if cube.cubies.get(p) is not None
          and len(cube.cubies[p].stickers) == 2}
    by = defaultdict(list)
    for p, g in wa.items():
        by[p5.slot_of(p)].append(g)
    return sum(1 for ids in by.values() if len(ids) == 2 and ids[0] == ids[1])


def _fixture_state(name):
    with open(os.path.join(GATE5B_DIR, name), encoding="utf-8") as f:
        fx = json.load(f)
    c = Cube5.solved()
    c.apply_moves(fx["scramble"])
    c.apply_moves(fx["center_moves"])
    c.apply_moves(fx["gate3_moves"])
    c.apply_moves(fx["gate4_moves"])
    c.apply_moves(fx["setup_moves"])
    c.apply_moves(fx["insert_moves"])
    return c


def test_pairer_preserves_centers_and_fixed_on_primitive():
    c = Cube5.solved()
    c.apply_moves(p5.P)
    assert centers_are_color_solved(c)
    assert _fixed_centers_preserved(c)


def test_pairer_pairs_on_wide_scramble():
    random.seed(5)
    c = Cube5.solved()
    for _ in range(40):
        c.apply_move(random.choice(WIDE))
    init = _matched(c)
    init_center_off = center_color_off(c)
    moves = p5.pair_edges(c)
    w = c.clone()
    w.apply_moves(moves)
    assert _matched(w) == 12
    assert center_color_off(w) == init_center_off, "配棱不应恶化中心错位"
    assert _fixed_centers_preserved(w), "配棱不应破坏固定面心"
    assert init < 12, "scramble 应至少拆散一组（单层转拆不散，必须用宽转）"


@pytest.mark.parametrize("name", sorted(os.listdir(GATE5B_DIR)))
def test_pairer_pairs_flip_fixtures(name):
    c = _fixture_state(name)
    assert centers_are_color_solved(c), "fixture 应已中心归面"
    init = _matched(c)
    assert init < 12
    moves = p5.pair_edges(c)
    w = c.clone()
    w.apply_moves(moves)
    assert _matched(w) == 12, f"{name} 未配齐"
    assert centers_are_color_solved(w), f"{name} 中心被破坏"
    assert _fixed_centers_preserved(w), f"{name} 固定面心被破坏"
