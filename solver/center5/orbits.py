"""5x5 中心位置轨道。

54 个中心位置在「合法动作」（外层 + 两层宽转）下被分成：
    FIXED  6 个单项点（六个绝对面心，固定参考件）
    CORNER 24 个（角/对角中心）
    EDGE   24 个（边/十字中心）

即轨道尺寸恒为 [1,1,1,1,1,1,24,24]。轨道成员由给定生成元自动计算，不硬编码。
每个轨道按其成员的局部坐标给出稳定语义名（CenterOrbitKind），不依赖 BFS 返回顺序。
"""

from enum import Enum
from typing import Dict, List, Sequence, Tuple

from cube.coordinates import FACE_AXIS_SIGN, TURNS, coord_values
from cube.notation import parse_move_full

Coord = Tuple[int, int, int]


class CenterOrbitKind(Enum):
    CORNER = "corner"
    EDGE = "edge"
    FIXED = "fixed"


def kind_of_position(pos: Coord) -> CenterOrbitKind:
    """按坐标绝对值把中心位置归入稳定语义轨道。"""
    mags = sorted(abs(v) for v in pos)
    if mags == [0, 0, 6]:
        return CenterOrbitKind.FIXED
    if mags == [3, 3, 6]:
        return CenterOrbitKind.CORNER
    if mags == [0, 3, 6]:
        return CenterOrbitKind.EDGE
    raise ValueError("不是 5x5 中心位置: %s" % (pos,))


def center_positions(n: int = 5) -> List[Coord]:
    """返回 5x5 所有中心位置（恰好贴 1 面）。"""
    from cube.coordinates import get_d_maxc
    d, maxc = get_d_maxc(n)
    vals = coord_values(n)
    out = []
    for x in vals:
        for y in vals:
            for z in vals:
                pos = (x, y, z)
                cnt = 0
                for axis, sign in FACE_AXIS_SIGN.values():
                    if pos[axis] == sign * maxc:
                        cnt += 1
                if cnt == 1:
                    out.append(pos)
    return out


def apply_to_pos(pos: Coord, move: str, n: int = 5) -> Coord:
    """对单个位置施加一个移动（统一支持 layers 前缀）。"""
    label, layers, count = parse_move_full(move)
    n_axis, n_sign = FACE_AXIS_SIGN[label]
    vals = sorted(coord_values(n), reverse=True)
    layer_vals = [n_sign * v for v in vals[:layers]]
    if pos[n_axis] not in layer_vals:
        return pos
    rot = TURNS[label]
    p = pos
    for _ in range(count):
        p = rot(*p)
    return p


def compute_center_orbits(
    generators: Sequence[str], n: int = 5
) -> List[List[Coord]]:
    """用并查集在给定生成元下计算中心位置的单点轨道。"""
    centers = center_positions(n)
    parent: Dict[Coord, Coord] = {}

    def find(a):
        path = []
        while parent[a] != a:
            path.append(a)
            a = parent[a]
        for p in path:
            parent[p] = a
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for p in centers:
        parent.setdefault(p, p)
    for p in centers:
        for m in generators:
            np = apply_to_pos(p, m, n)
            if np in parent:
                union(p, np)
    groups: Dict[Coord, set] = {}
    for p in centers:
        groups.setdefault(find(p), set()).add(p)
    return [sorted(g) for g in groups.values()]


def orbit_kinds(generators: Sequence[str], n: int = 5) -> Dict[CenterOrbitKind, List[Coord]]:
    """按语义轨道名聚合位置。"""
    result: Dict[CenterOrbitKind, List[Coord]] = {
        CenterOrbitKind.FIXED: [],
        CenterOrbitKind.CORNER: [],
        CenterOrbitKind.EDGE: [],
    }
    for orb in compute_center_orbits(generators, n):
        kind = kind_of_position(orb[0])
        result[kind].extend(orb)
    return result


def position_orbit_kind(pos: Coord) -> CenterOrbitKind:
    return kind_of_position(pos)
