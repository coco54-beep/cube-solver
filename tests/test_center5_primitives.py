"""5x5 活动中心 3-cycle 基元验真测试。

每个基元必须在合法动作下恰好循环对应轨道的 3 个中心，固定另一活动轨道与
6 个固定面心。验真通过「位置模拟」与「真实 Cube5 重放」双路径比对。
"""

import pytest

from cube.cube5 import Cube5
from solver.center5 import (
    CORNER_BACKUP,
    CORNER_MAIN,
    EDGE_BACKUP,
    EDGE_MAIN,
    CenterOrbitKind,
    analyze_cube5_replay,
    check_primitive_inverse,
    check_primitive_triple_restores_centers,
    is_legal_5x5_solver_move,
    validate_center_primitive,
)

ALL_PRIMITIVES = [CORNER_MAIN, CORNER_BACKUP, EDGE_MAIN, EDGE_BACKUP]


def test_module_has_main_and_backup_corner_and_edge():
    names = {p.name for p in ALL_PRIMITIVES}
    assert {"corner_main", "corner_backup", "edge_main", "edge_backup"} <= names
    orbits = {p.orbit for p in ALL_PRIMITIVES}
    assert CenterOrbitKind.CORNER in orbits
    assert CenterOrbitKind.EDGE in orbits


@pytest.mark.parametrize("p", ALL_PRIMITIVES, ids=lambda p: p.name)
def test_all_moves_legal(p):
    for move in p.moves:
        assert is_legal_5x5_solver_move(move)


@pytest.mark.parametrize("p", ALL_PRIMITIVES, ids=lambda p: p.name)
def test_primitive_is_pure_3cycle(p):
    analysis = validate_center_primitive(p)
    assert analysis.cycle_type() == (3,)
    assert len(analysis.moved_corner_centers) == (
        3 if p.orbit == CenterOrbitKind.CORNER else 0)
    assert len(analysis.moved_edge_centers) == (
        3 if p.orbit == CenterOrbitKind.EDGE else 0)
    assert not analysis.moved_fixed_centers


@pytest.mark.parametrize(
    "p", [p for p in ALL_PRIMITIVES if p.orbit == CenterOrbitKind.CORNER],
    ids=lambda p: p.name)
def test_corner_primitive_does_not_move_edge_or_fixed(p):
    analysis = validate_center_primitive(p)
    assert not analysis.moved_edge_centers
    assert not analysis.moved_fixed_centers
    assert analysis.cycle_type() == (3,)


@pytest.mark.parametrize(
    "p", [p for p in ALL_PRIMITIVES if p.orbit == CenterOrbitKind.EDGE],
    ids=lambda p: p.name)
def test_edge_primitive_does_not_move_corner_or_fixed(p):
    analysis = validate_center_primitive(p)
    assert not analysis.moved_corner_centers
    assert not analysis.moved_fixed_centers
    assert analysis.cycle_type() == (3,)


@pytest.mark.parametrize("p", ALL_PRIMITIVES, ids=lambda p: p.name)
def test_expected_cycle_matches_analysis(p):
    analysis = validate_center_primitive(p)
    assert analysis.center_cycles[0] == p.expected_cycle


@pytest.mark.parametrize("p", ALL_PRIMITIVES, ids=lambda p: p.name)
def test_inverse_restores_cube(p):
    assert check_primitive_inverse(p)


@pytest.mark.parametrize("p", ALL_PRIMITIVES, ids=lambda p: p.name)
def test_triple_restores_centers(p):
    assert check_primitive_triple_restores_centers(p)


def test_replay_on_cube5_matches_permutation_analysis():
    for p in ALL_PRIMITIVES:
        analysis = analyze_cube5_replay(p.moves, p.orbit)
        assert analysis.cycle_type() == (3,)
        assert analysis.center_cycles[0] == p.expected_cycle


def test_primitive_supports_are_disjoint_between_orbits():
    corner = validate_center_primitive(CORNER_MAIN)
    edge = validate_center_primitive(EDGE_MAIN)
    assert not (corner.moved_corner_centers & edge.moved_edge_centers)
    assert not corner.moved_edge_centers
    assert not edge.moved_corner_centers
