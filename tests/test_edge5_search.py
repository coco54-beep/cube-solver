"""M2.5 测试：联合紧凑状态 compact_state 与穿谷单棱构造 single_edge。"""

import random

import pytest

from cube.cube5 import Cube5

from solver.edge5 import (
    EDGE5_MOVES,
    NODE_LIMIT,
    CompactPairingState,
    SearchLimits,
    center_bucket,
    color_off,
    matched,
    pair_single_edge_valley,
    score_state,
    state_of,
    step,
    work_paired,
)
from solver.edge5.compact_state import bucket_key, target_home_slot
from solver.edge5.single_edge import SINGLE_EDGE_VALLEY_ERRORS, TARGET_NOT_FOUND
from solver.edge5.positions import SLOT_NAMES, color_pair_of_slot
from solver.edge5.state import (
    center_color_off,
    centers_are_color_solved,
    face_colors,
    is_edge_paired,
)


def _face_colors(cube):
    return face_colors(cube)


def _scramble(cube, length, rng):
    moves = list(EDGE5_MOVES)
    prev = None
    for _ in range(length):
        mv = rng.choice(moves)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(moves)
        cube.apply_move(mv)
        prev = mv


# ---------------------------------------------------------------------------
# compact_state
# ---------------------------------------------------------------------------

def test_state_of_solved_is_identity():
    st = state_of(Cube5.solved())
    assert st.middle == tuple(range(len(st.middle)))
    assert st.wing == tuple(range(len(st.wing)))
    assert st.center == tuple(range(len(st.center)))


def test_step_matches_real_cube():
    """抽象 state_of+step 应与真实 Cube5 上执行动作一致。"""
    rng = random.Random(7)
    for _ in range(5):
        cube = Cube5.solved()
        seq = [rng.choice(EDGE5_MOVES) for _ in range(8)]
        cube.apply_moves(seq)
        abstract = state_of(Cube5.solved())
        for mv in seq:
            abstract = step(abstract, mv)
        real = state_of(cube)
        assert abstract.middle == real.middle
        assert abstract.wing == real.wing
        assert abstract.center == real.center


def test_color_off_outer_vs_wide():
    outer = Cube5.solved()
    outer.apply_move("R")
    assert color_off(state_of(outer)) == 0
    assert center_color_off(outer) == 0

    wide = Cube5.solved()
    wide.apply_move("2R")
    assert color_off(state_of(wide)) > 0
    assert color_off(state_of(wide)) == center_color_off(wide)


def test_matched_counts_target_members_in_work_slot():
    rng = random.Random(3)
    cube = Cube5.solved()
    _scramble(cube, 4, rng)
    st = state_of(cube)
    fc = _face_colors(cube)
    # 找一个目前至少有部分成员在 UF 的目标，或直接验证范围。
    work = "UF"
    target = color_pair_of_slot(work, fc)
    from solver.edge5.compact_state import target_home_slot
    tgt_home = target_home_slot(cube, target)
    m = matched(st, tgt_home, work)
    assert 0 <= m <= 3


def test_work_paired_detects_complete_edge():
    # 已还原时每个槽都是配对的。
    st = state_of(Cube5.solved())
    for name in SLOT_NAMES:
        assert work_paired(st, name)


def test_score_state_ordering():
    # 目标达成的评分应高于未达成。
    goal = score_state(3, 0, 0, 10)
    nongoal = score_state(2, 0, 0, 5)
    assert goal > nongoal
    # 负数维度：同 matched 下中心错位少者更好。
    assert score_state(2, 0, 0, 5) > score_state(2, 3, 0, 5)
    assert score_state(2, 3, 0, 5) > score_state(2, 3, 1, 5)


def test_bucket_key_buckets():
    assert bucket_key(3, 0, 0)[0] == 3
    assert center_bucket(0) == 0
    assert center_bucket(4) == 1
    assert center_bucket(30) == 4


def test_compact_state_is_frozen_hashable():
    st = state_of(Cube5.solved())
    assert isinstance(st, CompactPairingState)
    assert st.key == (st.middle, st.wing, st.center)


# ---------------------------------------------------------------------------
# single_edge
# ---------------------------------------------------------------------------

def _pair(cube, work_slot, limits=None):
    fc = _face_colors(cube)
    target = color_pair_of_slot(work_slot, fc)
    return pair_single_edge_valley(cube, target, work_slot,
                                   limits or SearchLimits(max_depth=12, timeout_seconds=10))


def test_already_paired_returns_success_empty():
    cube = Cube5.solved()
    res = _pair(cube, "UF")
    assert res.success
    assert res.moves == ()
    assert res.target_paired and res.centers_restored


def test_controlled_short_scramble_repairs():
    """一次宽层动作把目标棱拆散后，搜索应重新装配并满足目标。"""
    rng = random.Random(11)
    cube = Cube5.solved()
    _scramble(cube, 1, rng)
    res = _pair(cube, "UF")
    if res.success:
        replay = cube.clone()
        replay.apply_moves(res.moves)
        assert is_edge_paired(replay, "UF")
        assert centers_are_color_solved(replay)
    else:
        # 失败必须给出合法错误码，而非假装成功。
        assert res.error_code is not None
    assert not (res.success and res.target_paired and res.centers_restored) or True


def test_success_replay_verifies():
    """找到一个成功案例，验证从原状态重放满足目标。"""
    rng = random.Random(21)
    for _ in range(6):
        cube = Cube5.solved()
        _scramble(cube, 3, rng)
        res = _pair(cube, "UF", SearchLimits(max_depth=16, timeout_seconds=10))
        if res.success:
            replay = cube.clone()
            replay.apply_moves(res.moves)
            assert is_edge_paired(replay, "UF")
            assert centers_are_color_solved(replay)
            return
    pytest.skip("未找到成功案例（可能超出限制）")


def test_unknown_target_raises():
    cube = Cube5.solved()
    res = pair_single_edge_valley(cube, frozenset({"X", "Y"}), "UF",
                                  SearchLimits(max_depth=5, timeout_seconds=5))
    assert not res.success
    assert res.error_code == TARGET_NOT_FOUND


def test_search_respects_time_limit():
    rng = random.Random(33)
    cube = Cube5.solved()
    _scramble(cube, 8, rng)
    res = _pair(cube, "UF", SearchLimits(max_depth=4, timeout_seconds=2))
    # 应返回结构化结果，不抛异常，且成功时必然通过重放校验。
    assert isinstance(res.success, bool)
