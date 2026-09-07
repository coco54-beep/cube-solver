"""Gate 5b 翻转 fixtures 回归：重建一致 + 统一翻转签名。

这些 fixture 来自 `completion_kind == FLIPPED` 的 Gate 5 结果（位置装配已完成、朝向翻转），
供 Gate 5b「双棱修正」复现与测试。验证：
1. 完整轨迹重建后与 state_fingerprint 一致；
2. 输出槽三块同槽但 `is_edge_paired` 为假（翻转，未真配对）；
3. 中心归面 + 固定面心保持；
4. 统一签名类 `SINGLE_TREDGE_FLIP`（中棱与两翼相反）。
"""
import json
import os

import pytest

from cube.cube5 import Cube5
from solver.edge5.state import is_edge_paired, centers_are_color_solved
from solver.edge5.free_slice import _fixed_centers_preserved
from solver.edge5.positions import slot
from cube.coordinates import FACE_NORMALS

GATE5B_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5b")

COLOR_ORDER = {"W": 0, "Y": 1, "G": 2, "B": 3, "R": 4, "O": 5}


def _fixture(name):
    with open(os.path.join(GATE5B_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def _reconstruct(fx):
    c = Cube5.solved()
    c.apply_moves(fx["scramble"])
    c.apply_moves(fx["center_moves"])
    c.apply_moves(fx["gate3_moves"])
    c.apply_moves(fx["gate4_moves"])
    c.apply_moves(fx["setup_moves"])
    c.apply_moves(fx["insert_moves"])
    return c


def _fingerprint(cube):
    return sorted((tuple(p), tuple(cu.home), tuple(sorted(cu.stickers.items())))
                  for p, cu in cube.cubies.items())


def _norm(x):
    if isinstance(x, dict):
        return sorted((k, _norm(v)) for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return tuple(_norm(v) for v in x)
    return x


def _flip_signature(cube, slotname):
    s = slot(slotname)
    f1, f2 = list(s.name)
    n1, n2 = FACE_NORMALS[f1], FACE_NORMALS[f2]
    cols = []
    for p in (s.middle, s.left_wing, s.right_wing):
        cub = cube.cubies.get(p)
        if cub is None or len(cub.stickers) != 2:
            return None
        cols.append((cub.stickers.get(n1), cub.stickers.get(n2)))
    et = frozenset(c for c in cols[0] if c is not None)
    if len(et) != 2:
        return None
    c1, c2 = sorted(et, key=lambda c: COLOR_ORDER[c])
    pat = []
    for (a, b) in cols:
        if (a, b) == (c1, c2):
            pat.append("+")
        elif (a, b) == (c2, c1):
            pat.append("-")
        else:
            pat.append("?")
    return "".join(pat)


@pytest.mark.parametrize("name", sorted(os.listdir(GATE5B_DIR)))
def test_gate5b_fixture_reconstructs_flipped(name):
    fx = _fixture(name)
    c = _reconstruct(fx)
    assert _norm(_fingerprint(c)) == _norm(fx["state_fingerprint"]), "重建态与指纹不一致"
    out = fx["output_slot"]
    assert not is_edge_paired(c, out), "fixture 应为翻转（未真配对）"
    assert centers_are_color_solved(c)
    assert _fixed_centers_preserved(c)
    pat = _flip_signature(c, out)
    assert pat in ("-++", "+--"), f"异常翻转签名 {pat}"
    assert fx["completion_kind"] == "FLIPPED"
    assert fx["signature_class"] == "SINGLE_TREDGE_FLIP"
