"""5x5 批次配棱（batch shared-slice）回归与可发现性测试。

覆盖：
- seed5「卡在 9 条」fixture 可重放重建（生成路径，非 pickle）。
- 已知 batch `2R U L2 U' 2R'` 固定动作效果：9→10、中心归面、保护组 9/9。
- `search_pure_body_batch` 能在该 fixture 上重新发现净增批次（不要求相同动作）。
"""
import pytest

from tests.edge_batch_fixtures import (
    load_seed5_stuck_at_9,
    load_seed9_stuck_at_8,
    load_seed11_stuck_at_7,
    EXPECTED_BATCH,
    EXPECTED_PAIRED_COUNT,
    EXPECTED_AFTER_PAIRED,
    SEED9_EXPECTED_BATCH,
    SEED9_EXPECTED_PAIRED_COUNT,
    SEED9_EXPECTED_AFTER_PAIRED,
)
from solver.edge5.batch_pairing import (
    search_pure_body_batch,
    search_store_prefixed_batch,
    search_inner_store_batch,
    is_successful_batch,
    BatchSearchLimits,
)
from solver.edge5.state import centers_are_color_solved, is_edge_paired, paired_count
from solver.edge5.pairing_transaction import extract_paired_tredges, is_tredge_group_paired


def test_seed5_fixture_reconstructs_at_9():
    cube = load_seed5_stuck_at_9()
    assert centers_are_color_solved(cube)
    assert paired_count(cube) == EXPECTED_PAIRED_COUNT
    # 该状态确实有 9 条保护组。
    assert len(extract_paired_tredges(cube)) == EXPECTED_PAIRED_COUNT


def test_seed5_known_batch_moves_9_to_10():
    cube = load_seed5_stuck_at_9()
    protected = extract_paired_tredges(cube)

    cube.apply_moves(EXPECTED_BATCH)

    assert paired_count(cube) == EXPECTED_AFTER_PAIRED
    assert centers_are_color_solved(cube)
    assert all(is_tredge_group_paired(cube, g) for g in protected)


def test_seed9_stuck_at_8_reconstructs():
    cube = load_seed9_stuck_at_8()
    assert centers_are_color_solved(cube)
    assert paired_count(cube) == 8
    assert len(extract_paired_tredges(cube)) == 8


def test_seed9_known_store_prefixed_batch_moves_8_to_9():
    cube = load_seed9_stuck_at_8()
    protected = extract_paired_tredges(cube)

    cube.apply_moves(SEED9_EXPECTED_BATCH)

    assert paired_count(cube) == SEED9_EXPECTED_AFTER_PAIRED
    assert centers_are_color_solved(cube)
    assert all(is_tredge_group_paired(cube, g) for g in protected)


@pytest.mark.slow
def test_store_prefixed_batch_search_rediscovers_seed9_gain():
    cube = load_seed9_stuck_at_8()

    res = search_store_prefixed_batch(
        cube,
        max_store_depth=4,
        max_bodies=2,
        pure_limits=BatchSearchLimits(max_bodies=2, max_combos_per_open=600),
    )

    assert res.success
    assert res.paired_before == 8
    assert res.paired_after >= 9
    assert res.protected_survived
    assert res.replay_consistent

    replay = load_seed9_stuck_at_8()
    for mv in res.moves:
        replay.apply_move(mv)
    assert paired_count(replay) == res.paired_after
    assert centers_are_color_solved(replay)


@pytest.mark.slow
def test_pure_body_batch_search_rediscovers_seed5_gain():
    cube = load_seed5_stuck_at_9()

    result = search_pure_body_batch(cube, max_bodies=2)

    assert result.success
    assert result.paired_before == 9
    assert result.paired_after >= 10
    assert not result.protected_broken
    assert result.replay_consistent

    # 搜索动作从原始状态重放应达到相同后置条件。
    replay = load_seed5_stuck_at_9()
    for mv in result.moves:
        replay.apply_move(mv)
    assert paired_count(replay) == result.paired_after
    assert centers_are_color_solved(replay)


def test_inner_store_batch_contract_seed11():
    """`search_inner_store_batch` 在小预算下应快速返回结构正确的 BatchPairingResult。

    当前 seed11/20 的 7→8 是开放难题（见 PAIRING_BREAKTHROUGH.md），因此这里不放宽到
    成功，只校验搜索契约：成功时动作可重放生效且保护组一致；失败时返回 NO_INNER_STORE_BATCH。
    """
    cube = load_seed11_stuck_at_7()
    protected = extract_paired_tredges(cube)

    res = search_inner_store_batch(
        cube,
        max_store_depth=2,
        max_bodies=2,
        max_bodies_per_open=3,
        max_store_paths_per_group=2,
        max_checked=200,
        allowed_open_moves=("2B", "2D"),
        limits=BatchSearchLimits(max_bodies=2),
    )

    assert res is not None
    assert res.paired_before == paired_count(cube)
    assert res.protected_before == protected
    assert res.replay_consistent
    if res.success:
        assert res.paired_after >= res.paired_before + 1
        replay = load_seed11_stuck_at_7()
        for mv in res.moves:
            replay.apply_move(mv)
        assert paired_count(replay) == res.paired_after
        assert centers_are_color_solved(replay)
        assert all(is_tredge_group_paired(replay, g) for g in protected)
    else:
        assert res.error_code == "NO_INNER_STORE_BATCH"
