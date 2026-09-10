"""5x5 中心求解器（solver.center5.solve_centers5）回归测试。

覆盖：（1）20 个固定 seed 的随机打乱回归；（2）已解输入返回空；
（3）动作全部合法；（4）同输入结果确定；（5）固定面心不被扰动；
（6）validate_5x5 校验通过；（7）整机校验；（8）输入对象不被修改；
（9）setup 缓存性能（存在随包预建表时 builds==0，否则首次 builds==2；二次 hits>0）。
"""

import random

import pytest

from cube.cube5 import Cube5
from cube.conversion import cubies_to_facelets
from cube.validation import validate_5x5
from solver.center5 import (
    CenterSolveResult,
    LEGAL_5X5_CENTER_MOVES,
    assert_legal_5x5_solution_moves,
    kind_of_position,
    solve_centers5,
)
from solver.center5.orbits import CenterOrbitKind
from solver.center5.setup_cache import (
    clear_setup_cache,
    setup_cache_stats,
)

_ALL_LEGAL = tuple(LEGAL_5X5_CENTER_MOVES)


def make_legal_scramble(seed: int, length: int = 25) -> list:
    """确定性地生成一组合法 5x5 打乱动作（种子化）。"""
    rng = random.Random(seed)
    moves = []
    for _ in range(length):
        moves.append(rng.choice(_ALL_LEGAL))
    return moves


def _centers_solved(cube) -> bool:
    for cubie in cube.cubies.values():
        if len(cubie.stickers) == 1 and cubie.pos != cubie.home:
            return False
    return True


def _fixed_centers_at_home(cube) -> bool:
    for cubie in cube.cubies.values():
        if len(cubie.stickers) == 1:
            if kind_of_position(cubie.home) == CenterOrbitKind.FIXED and cubie.pos != cubie.home:
                return False
    return True


@pytest.mark.parametrize("seed", range(20))
def test_seed_regression(seed):
    scramble = make_legal_scramble(seed=seed, length=25)
    cube = Cube5.solved()
    cube.apply_moves(scramble)

    res = solve_centers5(cube)
    assert res.success, "seed %d 失败: %s" % (seed, res.message)
    assert isinstance(res, CenterSolveResult)

    replay = cube.clone()
    replay.apply_moves(list(res.moves))
    assert _centers_solved(replay), "重放后中心未全部还原"
    assert _fixed_centers_at_home(replay), "固定面心被扰动"

    facelets = cubies_to_facelets(replay.cubies, 5)
    assert validate_5x5(facelets) == [], "求解后整机状态非法"


def test_solved_input_returns_empty():
    cube = Cube5.solved()
    res = solve_centers5(cube)
    assert res.success
    assert res.moves == ()
    assert res.corner_cycle_count == 0
    assert res.edge_cycle_count == 0


def test_all_moves_legal():
    cube = Cube5.solved()
    cube.apply_moves(make_legal_scramble(seed=5, length=30))
    res = solve_centers5(cube)
    assert res.success
    assert_legal_5x5_solution_moves(list(res.moves))


def test_same_input_deterministic():
    cube = Cube5.solved()
    cube.apply_moves(make_legal_scramble(seed=9, length=25))
    a = solve_centers5(cube)
    b = solve_centers5(cube)
    assert a.moves == b.moves
    assert a.corner_cycle_count == b.corner_cycle_count
    assert a.edge_cycle_count == b.edge_cycle_count


def test_input_not_mutated():
    cube = Cube5.solved()
    cube.apply_moves(make_legal_scramble(seed=13, length=25))
    frozen = cube.clone()
    solve_centers5(cube)
    for pos, cubie in cube.cubies.items():
        assert cubie.pos == frozen.cubies[pos].pos
        assert cubie.home == frozen.cubies[pos].home


def test_parity_prefix_recorded_cross_combos():
    for seed in range(4):
        cube = Cube5.solved()
        cube.apply_moves(make_legal_scramble(seed=seed, length=25))
        res = solve_centers5(cube)
        assert res.success
        assert isinstance(res.parity_prefix, tuple) or res.parity_prefix == ()


def test_setup_cache_performance():
    clear_setup_cache()
    cube = Cube5.solved()
    cube.apply_moves(make_legal_scramble(seed=0, length=25))
    solve_centers5(cube)
    stats1 = setup_cache_stats()
    # 有随包预建表时命中 bundled（builds==0）；无预建表时两轨道各 BFS 一次。
    assert stats1.builds in (0, 2), "首次求解 BFS 次数异常：%d" % stats1.builds
    assert stats1.builds + stats1.bundled_hits + stats1.disk_hits >= 1, \
        "首次求解既未构建也未命中预建/磁盘表"

    solve_centers5(cube)
    stats2 = setup_cache_stats()
    assert stats2.builds == stats1.builds, "第二次求解不应重复 BFS"
    assert stats2.hits > stats1.hits, "第二次求解应命中缓存的 setup"
