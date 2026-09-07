"""Gate 5b 双棱目标→缓冲状态模型的结构验证（只验证模型自洽，不验证修正公式）。"""
import json
import os

import pytest

from cube.cube5 import Cube5
from solver.edge5.flip_transfer import (
    compute_flip_transfer_state,
    choose_unpaired_buffer_edge,
)
from solver.edge5.positions import (
    MIDDLE_ORDER, SLOT_NAMES, slot_of, slot,
)
from solver.edge5.compact_state import _SLOT_MID


def _home_slot_of_middle(middle_piece_id: int) -> str:
    mid_home = MIDDLE_ORDER[middle_piece_id]
    for name in SLOT_NAMES:
        if slot(name).middle == mid_home:
            return name
    raise AssertionError("no slot for middle home")


def _replay_fixture(path):
    with open(path, encoding="utf-8") as f:
        fx = json.load(f)
    c = Cube5.solved()
    for k in ("scramble", "center_moves", "gate3_moves", "gate4_moves",
              "setup_moves", "insert_moves"):
        c.apply_moves(fx[k])
    return fx, c


@pytest.fixture(params=sorted(os.listdir(
    os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5b"))))
def flip_fixture(request):
    d = os.path.join(os.path.dirname(__file__), "fixtures", "edge5", "gate5b")
    fx, cube = _replay_fixture(os.path.join(d, request.param))
    return fx, cube


def test_target_is_flipped(flip_fixture):
    fx, cube = flip_fixture
    target_slot = _home_slot_of_middle(fx["middle_piece_id"])
    hs = compute_flip_transfer_state(cube, target_a_slot=target_slot,
                                     buffer_b_slot="UR")
    assert hs.target_orientation == 1, "目标棱应携待转移翻转缺陷"


def test_choose_buffer_distinct_unpaired(flip_fixture):
    fx, cube = flip_fixture
    target_slot = _home_slot_of_middle(fx["middle_piece_id"])
    buf = choose_unpaired_buffer_edge(cube, target_a_slot=target_slot,
                                      protected_slots=(target_slot,))
    assert buf is not None, "应有可用缓冲棱"
    assert buf != target_slot


def test_transfer_state_structural(flip_fixture):
    fx, cube = flip_fixture
    target_slot = _home_slot_of_middle(fx["middle_piece_id"])
    buf = choose_unpaired_buffer_edge(cube, target_a_slot=target_slot,
                                      protected_slots=(target_slot,))
    hs = compute_flip_transfer_state(cube, target_a_slot=target_slot,
                                     buffer_b_slot=buf,
                                     protected_slots=())
    assert hs.target_a_slot != hs.buffer_b_slot
    assert len(hs.target_piece_positions) == 3
    assert len(hs.buffer_piece_positions) == 3
    assert hs.centers_solved
    assert hs.fixed_centers_preserved
    assert hs.protected_signature == ()
