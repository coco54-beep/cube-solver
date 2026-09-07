"""Gate 5b 规范化布局测试：目标 A 整体搬 UF、缓冲 B 中棱搬 UR/UB/UL。"""
import json
import os

import pytest

from cube.cube5 import Cube5
from solver.edge5.flip_layout import (
    normalize_flip_transfer, TARGET_SLOT, BUFFER_SLOTS,
)
from solver.edge5.flip_transfer import choose_unpaired_buffer_edge
from solver.edge5.positions import MIDDLE_ORDER, MIDDLE_INDEX, WING_ORDER, WING_INDEX, SLOT_NAMES, slot
from solver.edge5.compact_state import _SLOT_MID
from solver.edge5.state import centers_are_color_solved, is_edge_paired
from solver.edge5.free_slice import _fixed_centers_preserved


def _home_slot_of_middle(middle_piece_id: int) -> str:
    mid_home = MIDDLE_ORDER[middle_piece_id]
    for name in SLOT_NAMES:
        if slot(name).middle == mid_home:
            return name
    raise AssertionError("no slot for middle home")


def _cubie_pos(cube, home):
    for c in cube.cubies.values():
        if c.home == home:
            return c.pos
    return None


@pytest.fixture(params=sorted(os.listdir(
    os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5b"))))
def flip_fixture(request):
    d = os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5b")
    with open(os.path.join(d, request.param), encoding="utf-8") as f:
        fx = json.load(f)
    c = Cube5.solved()
    for k in ("scramble", "center_moves", "gate3_moves", "gate4_moves",
              "setup_moves", "insert_moves"):
        c.apply_moves(fx[k])
    return fx, c


def test_normalize_target_to_uf(flip_fixture):
    fx, cube = flip_fixture
    mids = fx["middle_piece_id"]
    wa, wb = fx["wing_a_piece_id"], fx["wing_b_piece_id"]
    buf_slot = choose_unpaired_buffer_edge(
        cube, target_a_slot=_home_slot_of_middle(mids),
        protected_slots=(_home_slot_of_middle(mids),))
    assert buf_slot is not None
    res = normalize_flip_transfer(
        cube,
        target_middle_home=MIDDLE_INDEX[MIDDLE_ORDER[mids]],
        target_wing_a_home=WING_INDEX[_wing_home(wa)],
        target_wing_b_home=WING_INDEX[_wing_home(wb)],
        buffer_middle_home=_SLOT_MID[buf_slot],
    )
    assert res.success, res.error_code
    # 应用 setup 后：中心归面、固定面心不动、目标三块搬到 UF。
    c2 = cube.clone()
    for mv in res.setup_moves:
        c2.apply_move(mv)
    assert centers_are_color_solved(c2)
    assert _fixed_centers_preserved(c2)
    uf = slot(TARGET_SLOT)
    assert _cubie_pos(c2, MIDDLE_ORDER[mids]) == uf.middle
    assert _cubie_pos(c2, _wing_home(wa)) == uf.left_wing
    assert _cubie_pos(c2, _wing_home(wb)) == uf.right_wing


def _wing_home(wing_piece_id):
    from solver.edge5.positions import WING_ORDER
    return WING_ORDER[wing_piece_id]
