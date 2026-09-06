"""5x5 中心位置轨道分析与基元分析工具。

关键数学事实（由移动引擎自动计算得出）：
    5x5 的 54 个中心位置在「面 + 宽层 + 内层」移动下分成 3 个单点轨道：
        face-center(sz6):   6 个面心位置            (一个非零坐标)
        corner(sz24):       角/对角中心位置         (一个 6 + 两个 3)
        edge(sz24):         边/十字中心位置         (一个 6 + 一个 3 + 一个 0)

    单点轨道说明中心只能在同轨道内互相到达；因此中心求解必须按轨道分别进行。
    本模块提供：位置轨道计算、位置分类、对单个位置施加移动、基元三槽分析。
"""

from typing import Dict, List, Tuple

from cube.coordinates import FACE_AXIS_SIGN, TURNS, coord_values
from cube.notation import parse_move_full

Coord = Tuple[int, int, int]

ORBIT_FACE_CENTER = "face-center(sz6)"
ORBIT_CORNER = "corner(sz24)"
ORBIT_EDGE = "edge(sz24)"


def classify_pos(pos: Coord) -> str:
    """按坐标绝对值把中心位置归类到某个单点轨道。"""
    mags = sorted(abs(v) for v in pos)
    if mags == [0, 0, 6]:
        return ORBIT_FACE_CENTER
    if mags == [3, 3, 6]:
        return ORBIT_CORNER
    if mags == [0, 3, 6]:
        return ORBIT_EDGE
    raise ValueError(f"不是 5x5 中心位置: {pos}")


def center_positions(n: int = 5) -> List[Coord]:
    """返回 5x5 所有中心位置（恰好贴 1 面）。"""
    d, maxc = _get_d_maxc(n)
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


def _get_d_maxc(n):
    from cube.coordinates import get_d_maxc
    return get_d_maxc(n)


def apply_to_pos(pos: Coord, move: str, n: int = 5) -> Coord:
    """对单个位置施加一个移动（layers 前缀、宽层、外层的统一定义）。"""
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


def build_move_generators(n: int = 5) -> List[str]:
    """求解器实际用到的移动生成元（外、宽、内层，含逆与 180）。"""
    gen = []
    for b in ["R", "L", "U", "D", "F", "B"]:
        for s in ["", "'", "2"]:
            gen.append(b + s)
            gen.append(b.lower() + s)
            for l in [2, 3, 4]:
                gen.append(str(l) + b + s)
    return sorted(set(gen))


def compute_single_point_orbits(n: int = 5, generators: List[str] = None) -> List[List[Coord]]:
    """用并查集计算中心位置的单点轨道。"""
    if generators is None:
        generators = build_move_generators(n)
    centers = center_positions(n)
    parent = {}

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


def position_orbit_map(n: int = 5, generators: List[str] = None) -> Dict[Coord, int]:
    """位置 -> orbit 索引。"""
    orbits = compute_single_point_orbits(n, generators)
    omap: Dict[Coord, int] = {}
    for i, orb in enumerate(orbits):
        for p in orb:
            omap[p] = i
    return omap


def orbit_class_counts(n: int = 5) -> Dict[str, int]:
    """每个轨道类别的位置数。"""
    from collections import Counter
    c = Counter(classify_pos(p) for p in center_positions(n))
    return dict(c)
