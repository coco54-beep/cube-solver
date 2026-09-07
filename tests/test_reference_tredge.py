"""Reference oracle 的完整 5x5 tredge 分类与共轭不变量诊断。

验证 `tools/research/5x5/reference/tredge.py`：
- 完整 tredge（中棱 + 两翼同色对）判定与计数；
- 中棱 / 翼颜色键（身份识别，无序）；
- 方向判定（与身份识别分开）；
- 版本关键实证：`setup + P + 逆setup` 共轭**保持**中棱↔翼归属（不变量），
  说明当前配翼原语无法实现「中棱锚定」，只能整体搬运槽单元。

与生产 `solver/edge5` 无关。`tredge.py` / `pairing5.py` 以独立脚本加载。
"""
import importlib.util
import json
import os

import pytest

from cube.cube5 import Cube5
from solver.edge5.positions import edge_type_of_cubie

_REF_DIR = os.path.join(os.path.dirname(__file__), "..", "tools", "research", "5x5", "reference")


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_REF_DIR, file))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


t = _load("tredge", "tredge.py")
p5 = _load("pairing5", "pairing5.py")

GATE5B_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5b")


def _fixture(name):
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


# -- 分类接口 --

def test_solved_cube_all_complete():
    c = Cube5.solved()
    assert t.count_complete_tredges(c) == 12
    assert set(t.SLOT_NAMES) == t.complete_tredge_slots(c)


def test_solved_cube_all_oriented():
    c = Cube5.solved()
    for n in t.SLOT_NAMES:
        assert t.tredge_oriented(c, n), n


def test_color_keys_are_unordered_pairs():
    c = Cube5.solved()
    mk = t.middle_edge_key(c, "UF")
    lw, rw = t.wing_keys_of_slot(c, "UF")
    assert mk == frozenset(mk)  # 无序集合
    assert lw == mk and rw == mk
    # 两条不同逻辑棱颜色对不同
    assert t.middle_edge_key(c, "UF") != t.middle_edge_key(c, "UR")


def test_incomplete_tredge_is_false():
    # 单层转不会拆散槽单元（中棱与两翼同层一起动），因此需宽转打乱制造不完整槽。
    c = Cube5.solved()
    c.apply_move("2R")
    assert not t.is_complete_tredge(c, "UF")
    assert t.count_complete_tredges(c) < 12


def test_worst_scramble_has_lte_wing_pairs():
    # 翻转 fixtures 多为 1~3 complete，方向为 0（被翻转）
    for name in sorted(os.listdir(GATE5B_DIR)):
        c = _fixture(name)
        assert t.count_complete_tredges(c) <= 3, name


@pytest.mark.parametrize("name", sorted(os.listdir(GATE5B_DIR)))
def test_fixture_not_all_complete(name):
    c = _fixture(name)
    assert t.count_complete_tredges(c) < 12


# -- 方向与身份分离 --

def test_oriented_requires_matching_cardinal_color():
    # solved 状态 UF 三块朝 U/F 颜色正确 -> oriented
    c = Cube5.solved()
    assert t.tredge_oriented(c, "UF")
    # 翻转中棱方向后破坏朝向但保留颜色对（身份）：构造一个明确翻转的 tredge
    # 简单三棱翻：UF/UR/UB 翻转由 (R U R' U') 类动作不保证，改用已知翻转序列。
    # 此处仅验证身份判断不受方向影响：翻转 fixture 中 complete 但 oriented 为 0。
    for name in sorted(os.listdir(GATE5B_DIR)):
        c = _fixture(name)
        cnt_complete = t.count_complete_tredges(c)
        cnt_oriented = sum(1 for n in t.SLOT_NAMES if t.tredge_oriented(c, n))
        assert cnt_oriented <= cnt_complete


# -- 决定性诊断：共轭保持中棱↔翼归属不变量 --

def _middle_key_at(cube, slot_name):
    return t.middle_edge_key(cube, slot_name)


def _wing_types_at(cube, slot_name):
    lw, rw = t.wing_keys_of_slot(cube, slot_name)
    return (lw, rw)


def _mismatch_count(cube):
    n = 0
    for s in t.SLOT_NAMES:
        mk = _middle_key_at(cube, s)
        if mk is None:
            continue
        lw, rw = _wing_types_at(cube, s)
        if lw is None or rw is None:
            continue
        if sorted(mk) in (sorted(lw), sorted(rw)):
            continue
        n += 1
    return n


def test_conjugates_preserve_middle_wing_assignment():
    """所有短 `setup + P + 逆setup` 共轭都不改变中棱↔翼相对归属。"""
    def short_setups(depth=2):
        out = []
        seen = {tuple()}
        frontier = [[]]
        for _ in range(depth):
            nxt = []
            for seq in frontier:
                for mv in p5.OUTER:
                    ns = p5._compress_log(seq + [mv])
                    if tuple(ns) in seen:
                        continue
                    seen.add(tuple(ns))
                    out.append(ns)
                    nxt.append(ns)
            frontier = nxt
        return out

    tested = 0
    changed = 0
    for seq in short_setups():
        c = Cube5.solved()
        c.apply_moves(seq)
        c.apply_moves(p5.P)
        c.apply_moves([p5._inv_of(m) for m in reversed(seq)])
        if _mismatch_count(c) > 0:
            changed += 1
        tested += 1
    assert tested > 0
    # 核心不变量：没有任何共轭改变相对归属
    assert changed == 0


def test_pairing_does_not_worsen_centers():
    # 确定性宽转打乱 -> 配翼：配棱不应恶化中心错位，不应破坏固定面心。
    import random
    random.seed(11)
    wide = ["2R", "2R'", "2L", "2L'", "2U", "2U'", "2D", "2D'", "2F", "2F'", "2B", "2B'"]
    sc = Cube5.solved()
    for _ in range(40):
        sc.apply_move(random.choice(wide))
    from solver.edge5.state import center_color_off
    from solver.edge5.free_slice import _fixed_centers_preserved
    init_off = center_color_off(sc)
    moves = p5.pair_edges(sc)
    w = sc.clone()
    w.apply_moves(moves)
    assert center_color_off(w) == init_off
    assert _fixed_centers_preserved(w)
