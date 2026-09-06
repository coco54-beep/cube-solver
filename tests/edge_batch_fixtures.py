"""可重放的 5x5 配棱批次 fixtures（JSON 轨迹 + 加载器）。

fixtures 记录从 solved 出发的**完整动作轨迹**（scramble + center_moves +
protected_pairing_moves），加载时只重放动作，不重新运行任何有搜索/耗时波动的
求解器，从而保证完全确定。数据位于 ``tests/fixtures/*.json``。
"""
from __future__ import annotations

import json
import os
from typing import Tuple

from cube.cube5 import Cube5
from solver.edge5.state import centers_are_color_solved, paired_count
from solver.edge5.pairing_transaction import extract_paired_tredges

_FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _read_fixture(name: str) -> dict:
    with open(os.path.join(_FIXTURES_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


def _replay_trajectory(data: dict) -> Cube5:
    cube = Cube5.solved()
    for seq_key in ("scramble", "center_moves", "protected_pairing_moves"):
        for mv in data.get(seq_key, ()):
            cube.apply_move(mv)
    return cube


def _assert_consistent(data: dict, cube: Cube5, expected_paired: int,
                       expected_centers: bool) -> None:
    assert centers_are_color_solved(cube) == expected_centers, (
        "centers not color-solved for fixture %s" % data.get("name"))
    assert paired_count(cube) == expected_paired, (
        "paired_count mismatch for fixture %s" % data.get("name"))


def _load_stuck_fixture(filename: str) -> Cube5:
    data = _read_fixture(filename)
    cube = _replay_trajectory(data)
    _assert_consistent(data, cube, data["expected_paired_count"],
                       data["expected_centers_solved"])
    return cube


def load_seed5_stuck_at_9() -> Cube5:
    return _load_stuck_fixture("seed5_stuck_at_9.json")


def load_seed9_stuck_at_8() -> Cube5:
    return _load_stuck_fixture("seed9_stuck_at_8.json")


def load_seed11_stuck_at_7() -> Cube5:
    return _load_stuck_fixture("seed11_stuck_at_7.json")


def load_seed20_stuck_at_7() -> Cube5:
    return _load_stuck_fixture("seed20_stuck_at_7.json")


def fixture_seed5_data() -> dict:
    return dict(_read_fixture("seed5_stuck_at_9.json"))


def fixture_seed9_data() -> dict:
    return dict(_read_fixture("seed9_stuck_at_8.json"))


# seed5 期望（保持原测试 API 兼容）。
EXPECTED_PAIRED_COUNT = 9
EXPECTED_BATCH = ("2R", "U", "L2", "U'", "2R'")
EXPECTED_AFTER_PAIRED = 10

# seed9 期望。
SEED9_EXPECTED_PAIRED_COUNT = 8
SEED9_EXPECTED_BATCH = ("R'", "U", "2B", "F'", "R'", "F", "R", "2B'")
SEED9_STORE_PREFIX = ("R'", "U")
SEED9_EXPECTED_AFTER_PAIRED = 9
