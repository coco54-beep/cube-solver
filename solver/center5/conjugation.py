"""5x5 中心 3-cycle 的共轭（conjugation）构造。

结论（已实证）：在合法动作下，corner / edge 中心轨道上的诱导作用是三重传递的
（3-transitive），即任一有序三重 (~12144 种) 都可达。于是对单个主基元 P，
总存在一个「setup」S（违反动作的任意合法短序列），使得
    S' + P + S
恰好作用出目标三重 (x, y, z)（与 P 的支撑三元组 (a,b,c) 通过 S 映射而来）。

本模块提供：
    find_setup      —— 用 BFS 找把 P 的支撑 (a,b,c) 映射到目标三重的 setup S。
    conjugate_cycle —— 输出 (S', P, S) 的完整合法动作序列。
"""

from collections import deque
from typing import List, Optional, Sequence, Tuple

from .legal_moves import invert_move_string, is_legal_5x5_solver_move
from .orbits import apply_to_pos, kind_of_position
from .primitives import CENTER_ORDER, CenterPrimitive

# 合法动作全集（外层 + 两层宽转 × {空,',2}）。
LEGAL_MOVES: Tuple[str, ...] = tuple(
    a + s for a in "RLUDFB" for s in ("", "'", "2")
) + tuple(
    "2" + a + s for a in "RLUDFB" for s in ("", "'", "2")
)

_LEGAL: Tuple[str, ...] = tuple(m for m in LEGAL_MOVES if is_legal_5x5_solver_move(m))


def find_setup(
    primitive: CenterPrimitive,
    target_ids: Sequence[int],
    max_states: int = 200000,
) -> Optional[Tuple[str, ...]]:
    """BFS 找最短 setup S，使 apply_to_pos 把基元支撑三元组映射到 target_ids。

    target_ids 是目标中心在 CENTER_ORDER 中的全局下标，必须属于基元轨道。
    找不到返回 None。
    """
    support = [CENTER_ORDER[i] for i in primitive.expected_cycle]
    start = tuple(support)
    target = tuple(CENTER_ORDER[i] for i in target_ids)
    if start == target:
        return ()
    seen = {start: ()}
    dq = deque([start])
    while dq:
        st = dq.popleft()
        if len(seen) >= max_states:
            return None
        for m in _LEGAL:
            ns = tuple(apply_to_pos(p, m, 5) for p in st)
            if ns not in seen:
                seen[ns] = seen[st] + (m,)
                if ns == target:
                    return seen[ns]
                dq.append(ns)
    return None


def conjugate_cycle(
    primitive: CenterPrimitive,
    target_ids: Sequence[int],
) -> List[str]:
    """返回作用出目标三重 (x,y,z) 的合法动作序列 S' P S。

    需先经 find_setup 求得 setup S。
    """
    setup = find_setup(primitive, target_ids)
    if setup is None:
        raise ValueError("无法为基元 %s 找到把支撑映射到 %s 的 setup"
                         % (primitive.name, list(target_ids)))
    moves: List[str] = []
    for m in reversed(setup):
        moves.append(invert_move_string(m))
    moves.extend(primitive.moves)
    moves.extend(setup)
    return moves
