"""5x5 活动中心（corner / edge 轨道）3-cycle 基元。

每个基元在合法动作下恰好循环对应轨道的 3 个中心，固定该轨道其余 21 个中心，
完全固定另一活动轨道以及 6 个绝对面心。棱/角的副作用允许（由后续阶段处理）。

正式库只存放少量经过自动验真的主/备用基元；搜索结果见 tools 下可复现脚本。
"""

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Sequence, Tuple

from cube.cube5 import Cube5

from .legal_moves import (
    assert_legal_5x5_solution_moves,
    invert_moves,
    is_legal_5x5_solver_move,
)
from .orbits import (
    CenterOrbitKind,
    center_positions,
    kind_of_position,
)

Coord = Tuple[int, int, int]

# 固定的中心位置全局索引（用于抽象 cycle/支持集标识）。
CENTER_ORDER: Tuple[Coord, ...] = tuple(sorted(center_positions(5)))
CENTER_INDEX: Dict[Coord, int] = {p: i for i, p in enumerate(CENTER_ORDER)}


def canonical_cycle(cycle: Tuple[int, ...]) -> Tuple[int, ...]:
    """把 cycle 旋转到以最小索引开头，得到与旋转无关的标准形式。"""
    if not cycle:
        return cycle
    m = cycle.index(min(cycle))
    return cycle[m:] + cycle[:m]


@dataclass(frozen=True)
class CenterPrimitive:
    name: str
    orbit: CenterOrbitKind
    moves: Tuple[str, ...]
    expected_cycle: Tuple[int, int, int]


@dataclass(frozen=True)
class PrimitiveAnalysis:
    center_cycles: Tuple[Tuple[int, ...], ...]
    moved_corner_centers: FrozenSet[int]
    moved_edge_centers: FrozenSet[int]
    moved_fixed_centers: FrozenSet[int]
    moved_edges: FrozenSet[Coord]
    moved_corners: FrozenSet[Coord]

    def cycle_type(self) -> Tuple[int, ...]:
        return tuple(sorted(len(c) for c in self.center_cycles))


# ---------------------------------------------------------------------------
# 工厂：官方主/备用基元
# ---------------------------------------------------------------------------

CORNER_MAIN = CenterPrimitive(
    name="corner_main",
    orbit=CenterOrbitKind.CORNER,
    moves=("2B", "2D", "F", "2D'", "2B'", "2D", "F'", "2D'"),
    expected_cycle=(0, 2, 18),
)

CORNER_BACKUP = CenterPrimitive(
    name="corner_backup",
    orbit=CenterOrbitKind.CORNER,
    moves=("2B", "2L", "F", "2L'", "2B'", "2L", "F'", "2L'"),
    expected_cycle=(18, 20, 51),
)

EDGE_MAIN = CenterPrimitive(
    name="edge_main",
    orbit=CenterOrbitKind.EDGE,
    moves=("2B2", "2D2", "L2", "2D2", "2B2", "2D2", "L2", "2D2"),
    expected_cycle=(3, 5, 48),
)

EDGE_BACKUP = CenterPrimitive(
    name="edge_backup",
    orbit=CenterOrbitKind.EDGE,
    moves=("2D2", "2B2", "R2", "2B2", "2D2", "2B2", "R2", "2B2"),
    expected_cycle=(1, 46, 52),
)

# 4 步联合换位子：一次做 edge 轨道 1 个 3-cycle + corner 轨道 2 个 3-cycle，
# 且不动 6 个固定面心。仅用于「先解 edge、再解 corner」的联合流程：
# edge 用它（更短），随后 corner 用 edge-pure 基元（不扰动已解 edge）。
# 注意：它会扰动 corner 轨道，故不通过 validate_center_primitive（后者要求另一轨道不动）。
EDGE_COMM4 = CenterPrimitive(
    name="edge_comm4",
    orbit=CenterOrbitKind.EDGE,
    moves=("2B", "D2", "2B'", "D2"),
    expected_cycle=(3, 21, 23),
)

CENTER_PRIMITIVES: Tuple[CenterPrimitive, ...] = (
    CORNER_MAIN, CORNER_BACKUP, EDGE_MAIN, EDGE_BACKUP,
)


# ---------------------------------------------------------------------------
# 置换分析（位置模拟，基于中心轨道）
# ---------------------------------------------------------------------------

def _position_cycle(moves: Sequence[str], orbit: CenterOrbitKind):
    """返回所有中心被循环的（home -> pos）映射。"""
    from .orbits import apply_to_pos
    homes = [p for p in CENTER_ORDER if kind_of_position(p) == orbit]
    mapping = {p: p for p in CENTER_ORDER}
    for m in moves:
        nm = {}
        for p, h in mapping.items():
            nm[apply_to_pos(p, m, 5)] = h
        mapping = nm
    return mapping, homes


def analyze_center_permutation(moves: Sequence[str], orbit: CenterOrbitKind):
    """基于位置模拟分析中心置换，返回 (cycles, moved_home_indices)。"""
    mapping, homes = _position_cycle(moves, orbit)
    # 反转得到 home -> pos 方向，使与真实 Cube5 重放的循环方向一致。
    forward = {p: h for h, p in mapping.items()}
    seen = set(); cycles = []
    moved = set()
    for p in CENTER_ORDER:
        if mapping[p] != p:
            moved.add(CENTER_INDEX[p])
    for hp in homes:
        if mapping[hp] == hp:
            continue
        cur = hp; cyc = []
        while cur not in seen:
            seen.add(cur); cyc.append(cur); cur = forward[cur]
        if len(cyc) > 1:
            cycles.append(canonical_cycle(tuple(CENTER_INDEX[x] for x in cyc)))
    return tuple(cycles), frozenset(moved)


# ---------------------------------------------------------------------------
# 真实 Cube5 重放分析
# ---------------------------------------------------------------------------

def analyze_cube5_replay(moves: Sequence[str], orbit: CenterOrbitKind) -> PrimitiveAnalysis:
    cube = Cube5.solved()
    cube.apply_moves(moves)
    homer = {}
    for c in cube.cubies.values():
        homer.setdefault(c.home, c)
    # 中心置换（home -> pos）
    center_cycles = []
    corner_centers = set(); edge_centers = set(); fixed_centers = set()
    edge_move = set(); corner_move = set()
    for c in cube.cubies.values():
        if c.home == c.pos:
            continue
        if len(c.stickers) == 3:
            corner_move.add(c.home)
        elif len(c.stickers) == 2:
            edge_move.add(c.home)
        elif len(c.stickers) == 1:
            k = kind_of_position(c.home)
            if k == CenterOrbitKind.CORNER:
                corner_centers.add(CENTER_INDEX[c.home])
            elif k == CenterOrbitKind.EDGE:
                edge_centers.add(CENTER_INDEX[c.home])
            else:
                fixed_centers.add(CENTER_INDEX[c.home])
    # 计算中心 cycle（限制在 orbit 的 home 上）
    seen = set()
    homes = [p for p in CENTER_ORDER if kind_of_position(p) == orbit]
    for hp in homes:
        if hp in seen:
            continue
        if homer.get(hp) is None or homer[hp].pos == hp:
            seen.add(hp)
            continue
        cyc = []; cur = hp
        while cur not in seen:
            seen.add(cur); cyc.append(cur); cur = homer[cur].pos
        if len(cyc) > 1:
            center_cycles.append(canonical_cycle(tuple(CENTER_INDEX[x] for x in cyc)))
    return PrimitiveAnalysis(
        center_cycles=tuple(center_cycles),
        moved_corner_centers=frozenset(corner_centers),
        moved_edge_centers=frozenset(edge_centers),
        moved_fixed_centers=frozenset(fixed_centers),
        moved_edges=frozenset(edge_move),
        moved_corners=frozenset(corner_move),
    )


# ---------------------------------------------------------------------------
# 验真
# ---------------------------------------------------------------------------

def validate_center_primitive(primitive: CenterPrimitive) -> PrimitiveAnalysis:
    """对基元做自动验真并返回支持集分析。

    校验项：
        1. 全部动作合法。
        2. 位置模拟与真实 Cube5 重放的中心 cycle 一致。
        3. 恰好一个 3-cycle，且属于声明轨道。
        4. 不移动另一活动轨道与 6 个固定面心。
        5. 逆序列复原，三次重复足以让中心复原（单独验证）。
    """
    moves = list(primitive.moves)
    assert_legal_5x5_solution_moves(moves)
    # 位置模拟
    sim_cycles, sim_moved = analyze_center_permutation(moves, primitive.orbit)
    # 真实重放
    replay = analyze_cube5_replay(moves, primitive.orbit)
    # 位置模拟与重放应一致
    assert tuple(sorted(sim_cycles)) == tuple(sorted(replay.center_cycles)), \
        "位置模拟与 Cube5 重放的中心 cycle 不一致"
    # 单一 3-cycle
    assert len(replay.center_cycles) == 1
    assert len(replay.center_cycles[0]) == 3
    # 与声明轨道一致
    other = [k for k in (CenterOrbitKind.CORNER, CenterOrbitKind.EDGE)
             if k != primitive.orbit]
    moved_other = (replay.moved_corner_centers
                   if other[0] == CenterOrbitKind.CORNER
                   else replay.moved_edge_centers)
    assert not moved_other, "基元移动了另一活动轨道"
    assert not replay.moved_fixed_centers, "基元移动了固定面心"
    return replay


def check_primitive_inverse(primitive: CenterPrimitive) -> bool:
    """逆序列是否能复原整个魔方。"""
    cube = Cube5.solved()
    cube.apply_moves(list(primitive.moves) + invert_moves(primitive.moves))
    return cube.is_solved()


def check_primitive_triple_restores_centers(primitive: CenterPrimitive) -> bool:
    """基元连续执行 3 次应让所有中心复原（棱/角不要求）。"""
    cube = Cube5.solved()
    cube.apply_moves(list(primitive.moves) * 3)
    for c in cube.cubies.values():
        if len(c.stickers) == 1 and c.pos != c.home:
            return False
    return True
