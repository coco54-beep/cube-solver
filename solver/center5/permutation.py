"""5x5 活动中心（corner / edge 轨道）的置换抽象与组合。

方向约定（冻结，勿改动）：
    permutation[pos] = home
即「位于位置 pos 的中心块最终应移动到 home」。全部中心求解逻辑基于该方向，
不再允许隐式切换。对应到基元共轭：
    conjugate_cycle(prim, (a, b, c))   —— 正向位置置换 a→b, b→c, c→a。
于是求解某轨道需把「pos -> home」映射分解为正向 3-cycle 之积（见
decompose_even_pos_to_home），切忌分解成 home -> pos（会导致死循环）。

本模块用于把 Cube5 某轨道的中心状态抽象成 24 元置换，以便做奇偶判断与
3-cycle 分解，并可与基元共轭（setup_cache + conjugate_cycle）对接。
"""

from typing import Sequence, Tuple

from cube.cube5 import Cube5

from .orbits import CenterOrbitKind, kind_of_position
from .primitives import CENTER_INDEX, CENTER_ORDER

# 该轨道 24 个中心的全局中心下标（按 CENTER_ORDER 排序，确定性）。
_ORBIT_GLOBAL_IDS: dict = {
    CenterOrbitKind.CORNER: tuple(
        i for i, p in enumerate(CENTER_ORDER)
        if kind_of_position(p) == CenterOrbitKind.CORNER
    ),
    CenterOrbitKind.EDGE: tuple(
        i for i, p in enumerate(CENTER_ORDER)
        if kind_of_position(p) == CenterOrbitKind.EDGE
    ),
}

# 全局下标 -> 0..23 稠密下标。
_ORBIT_DENSE: dict = {
    kind: {g: d for d, g in enumerate(ids)}
    for kind, ids in _ORBIT_GLOBAL_IDS.items()
}

Permutation = Tuple[int, ...]  # 24 元，permutation[pos_dense] = home_dense

_ACTIVE_ORBITS: Tuple[CenterOrbitKind, ...] = (
    CenterOrbitKind.CORNER,
    CenterOrbitKind.EDGE,
)


def orbit_global_ids(orbit: CenterOrbitKind) -> Tuple[int, ...]:
    """返回该轨道 24 个中心的全局中心下标（稠密序）。"""
    return _ORBIT_GLOBAL_IDS[orbit]


def build_pos_to_home_permutation(
    cube: Cube5,
    orbit: CenterOrbitKind,
) -> Permutation:
    """从 Cube5 读取某轨道中心状态，返回 24 元 pos->home 置换。

    permutation[pos_dense] = home_dense。要求该轨道恰有 24 个贴 1 面的中心。
    """
    dense = _ORBIT_DENSE[orbit]
    perm = [0] * 24
    seen = 0
    for pos, cubie in cube.cubies.items():
        if len(cubie.stickers) != 1:
            continue
        if kind_of_position(cubie.home) != orbit:
            continue
        g_pos = CENTER_INDEX[pos]
        g_home = CENTER_INDEX[cubie.home]
        perm[dense[g_pos]] = dense[g_home]
        seen += 1
    if seen != 24:
        raise ValueError(
            "轨道 %s 中的中心数量应为 24，实际 %d" % (orbit.value, seen)
        )
    return tuple(perm)


def permutation_parity(permutation: Sequence[int]) -> int:
    """置换奇偶（0 为偶，1 为奇）。"""
    n = len(permutation)
    seen = [False] * n
    s = 0
    for i in range(n):
        if seen[i]:
            continue
        j = i
        ln = 0
        while not seen[j]:
            seen[j] = True
            j = permutation[j]
            ln += 1
        s += ln - 1
    return s % 2


def _cycles_of(permutation: Sequence[int]) -> Tuple[Tuple[int, ...], ...]:
    """按置换边分解为不相交循环（循环内为正向顺序，perm[c_i] = c_{i+1}）。"""
    n = len(permutation)
    seen = [False] * n
    out = []
    for i in range(n):
        if seen[i]:
            continue
        cyc = []
        j = i
        while not seen[j]:
            seen[j] = True
            cyc.append(j)
            j = permutation[j]
        if len(cyc) > 1:
            out.append(tuple(cyc))
    return tuple(out)


def _apply_forward_cycle(
    permutation: Sequence[int],
    cycle: Tuple[int, int, int],
) -> list:
    """对置换施加「正向 3-cycle」移动映射 (a->b, b->c, c->a) 后的结果。

    移动映射 g: g(a)=b, g(b)=c, g(c)=a。施加后 f' = f ∘ g^{-1}：
        f'(a)=f(c), f'(b)=f(a), f'(c)=f(b)。
    """
    a, b, c = cycle
    out = list(permutation)
    pa, pb, pc = permutation[a], permutation[b], permutation[c]
    out[a] = pc
    out[b] = pa
    out[c] = pb
    return out


def decompose_even_pos_to_home(permutation: Sequence[int]) -> Tuple[Tuple[int, int, int], ...]:
    """把偶置换分解为正向 3-cycle 序列（a->b, b->c, c->a）。

    仅适用于奇偶为 0 的 pos->home 置换；对奇置换抛 ValueError。
    每个返回三元组可直接传给 conjugate_cycle(prim, (a, b, c))。
    分解过程对每步重新验证组合一致性（调试期断言）。
    """
    if permutation_parity(permutation) != 0:
        raise ValueError("decompose_even_pos_to_home 仅接受偶置换")
    work = list(permutation)
    out = []
    guard = 0
    while True:
        if all(work[i] == i for i in range(len(work))):
            break
        guard += 1
        if guard > 200:
            raise RuntimeError("3-cycle 分解未收敛")
        cycles = _cycles_of(work)
        big = [c for c in cycles if len(c) >= 3]
        if big:
            cyc = big[0]
            trip = (cyc[0], cyc[1], cyc[2])
        else:
            twos = [c for c in cycles if len(c) == 2]
            if len(twos) < 2:
                raise RuntimeError("残留奇置换（2-cycle 不能单独由 3-cycle 消解）")
            (a, b), (c, d) = twos[0], twos[1]
            trip = (a, b, c)
            out.append(trip)
            work = _apply_forward_cycle(work, trip)
            out.append((a, d, c))
            work = _apply_forward_cycle(work, (a, d, c))
            continue
        out.append(trip)
        work = _apply_forward_cycle(work, trip)
    return tuple(out)


def compose_cycles(cycles: Sequence[Tuple[int, int, int]]) -> list:
    """把正向 3-cycle 序列复合回置换（用于调试回归校验）。

    返回 g_total = ck ∘ ... ∘ c1 的位置映射数组，应与分解前的 permutation 相等。
    """
    g = list(range(24))
    for (a, b, c) in cycles:
        raw = {a: b, b: c, c: a}
        g = [raw.get(v, v) for v in g]
    return g


def assert_decomposition_valid(permutation: Sequence[int]) -> None:
    """校验 decompose 出的 cycle 能重组成原置换。"""
    cycles = decompose_even_pos_to_home(permutation)
    recomposed = compose_cycles(cycles)
    assert recomposed == list(permutation), (
        "3-cycle 分解重组合失败: %s != %s" % (recomposed, list(permutation))
    )
