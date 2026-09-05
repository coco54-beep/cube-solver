"""5x5 中心求解器（降阶第一阶段）。

策略：中心阶段内建奇偶翻转。
    1. 读取打乱后两个活动轨道（corner / edge）的 pos->home 置换与奇偶。
    2. 按奇偶前缀表施加极短前缀，把两轨道奇偶归一化（均为偶）。
    3. 对每个轨道，把偶置换分解为正向 3-cycle，用「S' P S」共轭逐一作用。
       两轨道共轭互不扰动（已实证），故可独立按 corner -> edge 顺序求解。
    4. 从原状态重放全部动作验证中心已还原，重放不符则返回失败诊断。

本模块对外只导出 `CenterSolveResult` 与 `solve_centers5`。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from cube.cube5 import Cube5

from .legal_moves import assert_legal_5x5_solution_moves
from .orbits import CenterOrbitKind, kind_of_position
from .permutation import (
    build_pos_to_home_permutation,
    decompose_even_pos_to_home,
    orbit_global_ids,
    permutation_parity,
)
from .primitives import CORNER_MAIN, EDGE_MAIN, CenterPrimitive
from .setup_cache import (
    SetupTable,
    SetupCacheStats,
    get_setup_table,
    instantiate_center_3cycle,
    setup_cache_stats,
)

# 奇偶前缀表：key=(corner_parity, edge_parity)，value=前缀动作串。
PARITY_PREFIX: dict = {
    (0, 0): (),
    (1, 0): ("2R",),
    (1, 1): ("R",),
    (0, 1): ("2R", "R"),
}

# 失败错误码。
FIXED_CENTER_INVALID = "FIXED_CENTER_INVALID"
CENTER_ASSIGNMENT_FAILED = "CENTER_ASSIGNMENT_FAILED"
CENTER_PARITY_NOT_NORMALIZED = "CENTER_PARITY_NOT_NORMALIZED"
SETUP_TARGET_UNREACHABLE = "SETUP_TARGET_UNREACHABLE"
CENTER_ORBIT_NOT_SOLVED = "CENTER_ORBIT_NOT_SOLVED"
CENTERS_NOT_SOLVED = "CENTERS_NOT_SOLVED"
CENTER_REPLAY_MISMATCH = "CENTER_REPLAY_MISMATCH"

_ACTIVE_ORBITS: Tuple[CenterOrbitKind, ...] = (
    CenterOrbitKind.CORNER,
    CenterOrbitKind.EDGE,
)


@dataclass(frozen=True)
class CenterSolveResult:
    """中心求解结果与诊断。"""

    success: bool
    moves: Tuple[str, ...]
    initial_corner_parity: int
    initial_edge_parity: int
    parity_prefix: Tuple[str, ...]
    corner_cycle_count: int
    edge_cycle_count: int
    setup_cache_hits: int
    setup_cache_builds: int
    message: str = ""
    error_code: Optional[str] = None


def choose_center_parity_prefix(
    corner_parity: int,
    edge_parity: int,
) -> Tuple[str, ...]:
    """按两轨道奇偶查前缀表。"""
    return PARITY_PREFIX[(corner_parity, edge_parity)]


# ---------------------------------------------------------------------------
# 校验辅助
# ---------------------------------------------------------------------------

def all_centers_solved(cube: Cube5) -> bool:
    """所有贴 1 面的中心块是否都在 home 位。"""
    for cubie in cube.cubies.values():
        if len(cubie.stickers) == 1 and cubie.pos != cubie.home:
            return False
    return True


def _validate_fixed_face_centers(cube: Cube5) -> bool:
    """六个绝对面心是否都在自身 home 位。"""
    for cubie in cube.cubies.values():
        if len(cubie.stickers) == 1 and kind_of_position(cubie.home) == CenterOrbitKind.FIXED:
            if cubie.pos != cubie.home:
                return False
    return True


def _record(working: Cube5, moves: List[str], seq: Sequence[str]) -> None:
    working.apply_moves(list(seq))
    moves.extend(seq)


def _primitive_for(orbit: CenterOrbitKind) -> CenterPrimitive:
    return CORNER_MAIN if orbit == CenterOrbitKind.CORNER else EDGE_MAIN


# ---------------------------------------------------------------------------
# 正式求解流程
# ---------------------------------------------------------------------------

def solve_centers5(cube: Cube5) -> CenterSolveResult:
    original = cube.clone()
    working = cube.clone()
    moves: List[str] = []

    before = setup_cache_stats()

    if not _validate_fixed_face_centers(working):
        return CenterSolveResult(
            success=False, moves=(), initial_corner_parity=0, initial_edge_parity=0,
            parity_prefix=(), corner_cycle_count=0, edge_cycle_count=0,
            setup_cache_hits=0, setup_cache_builds=0,
            error_code=FIXED_CENTER_INVALID, message="六个绝对面心被置于非 home 位",
        )

    corner_perm = build_pos_to_home_permutation(working, CenterOrbitKind.CORNER)
    edge_perm = build_pos_to_home_permutation(working, CenterOrbitKind.EDGE)
    initial_corner_parity = permutation_parity(corner_perm)
    initial_edge_parity = permutation_parity(edge_perm)

    prefix = choose_center_parity_prefix(initial_corner_parity, initial_edge_parity)
    _record(working, moves, prefix)

    cycle_counts = {CenterOrbitKind.CORNER: 0, CenterOrbitKind.EDGE: 0}
    def _orbit_is_solved(cube, orbit):
        for cubie in cube.cubies.values():
            if len(cubie.stickers) == 1 and kind_of_position(cubie.home) == orbit:
                if cubie.pos != cubie.home:
                    return False
        return True

    for orbit in _ACTIVE_ORBITS:
        perm = build_pos_to_home_permutation(working, orbit)
        if permutation_parity(perm) != 0:
            return CenterSolveResult(
                success=False, moves=tuple(moves),
                initial_corner_parity=initial_corner_parity,
                initial_edge_parity=initial_edge_parity,
                parity_prefix=prefix,
                corner_cycle_count=cycle_counts[CenterOrbitKind.CORNER],
                edge_cycle_count=cycle_counts[CenterOrbitKind.EDGE],
                setup_cache_hits=0, setup_cache_builds=0,
                error_code=CENTER_PARITY_NOT_NORMALIZED,
                message="奇偶前缀后轨道 %s 奇偶仍非 0" % orbit.value,
            )
        primitive = _primitive_for(orbit)
        table = get_setup_table(primitive)
        ids = orbit_global_ids(orbit)
        for trip in decompose_even_pos_to_home(perm):
            target = tuple(ids[x] for x in trip)
            try:
                macro = instantiate_center_3cycle(primitive, target, table)
            except ValueError:
                return CenterSolveResult(
                    success=False, moves=tuple(moves),
                    initial_corner_parity=initial_corner_parity,
                    initial_edge_parity=initial_edge_parity,
                    parity_prefix=prefix,
                    corner_cycle_count=cycle_counts[CenterOrbitKind.CORNER],
                    edge_cycle_count=cycle_counts[CenterOrbitKind.EDGE],
                    setup_cache_hits=0, setup_cache_builds=0,
                    error_code=SETUP_TARGET_UNREACHABLE,
                    message="轨道 %s 的目标三重不可达" % orbit.value,
                )
            _record(working, moves, macro)
            cycle_counts[orbit] += 1
        if not _orbit_is_solved(working, orbit):
            return CenterSolveResult(
                success=False, moves=tuple(moves),
                initial_corner_parity=initial_corner_parity,
                initial_edge_parity=initial_edge_parity,
                parity_prefix=prefix,
                corner_cycle_count=cycle_counts[CenterOrbitKind.CORNER],
                edge_cycle_count=cycle_counts[CenterOrbitKind.EDGE],
                setup_cache_hits=0, setup_cache_builds=0,
                error_code=CENTER_ORBIT_NOT_SOLVED,
                message="轨道 %s 求解后未回到 home" % orbit.value,
            )

    if not all_centers_solved(working):
        return CenterSolveResult(
            success=False, moves=tuple(moves),
            initial_corner_parity=initial_corner_parity,
            initial_edge_parity=initial_edge_parity,
            parity_prefix=prefix,
            corner_cycle_count=cycle_counts[CenterOrbitKind.CORNER],
            edge_cycle_count=cycle_counts[CenterOrbitKind.EDGE],
            setup_cache_hits=0, setup_cache_builds=0,
            error_code=CENTERS_NOT_SOLVED, message="中心未全部还原",
        )

    assert_legal_5x5_solution_moves(moves)

    # 从原状态重放，防止 working 状态与返回动作不一致。
    replay = original.clone()
    replay.apply_moves(moves)
    if not all_centers_solved(replay):
        return CenterSolveResult(
            success=False, moves=tuple(moves),
            initial_corner_parity=initial_corner_parity,
            initial_edge_parity=initial_edge_parity,
            parity_prefix=prefix,
            corner_cycle_count=cycle_counts[CenterOrbitKind.CORNER],
            edge_cycle_count=cycle_counts[CenterOrbitKind.EDGE],
            setup_cache_hits=0, setup_cache_builds=0,
            error_code=CENTER_REPLAY_MISMATCH,
            message="重放返回动作后中心未还原",
        )

    after = setup_cache_stats()
    return CenterSolveResult(
        success=True,
        moves=tuple(moves),
        initial_corner_parity=initial_corner_parity,
        initial_edge_parity=initial_edge_parity,
        parity_prefix=prefix,
        corner_cycle_count=cycle_counts[CenterOrbitKind.CORNER],
        edge_cycle_count=cycle_counts[CenterOrbitKind.EDGE],
        setup_cache_hits=after.hits - before.hits,
        setup_cache_builds=after.builds - before.builds,
    )
