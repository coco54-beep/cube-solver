"""整段动作化简：把任意 5x5 求解动作串折叠为等价的最短物理层动作。

原理：把每个动作映射为「绕某轴、对某些层坐标的带符号 90 度计数」。
- 外层/宽二层动作：`label, layers, count` -> 轴 = FACE_AXIS_SIGN[label][0]，
  层坐标 = layer_values(n, label, layers)，带符号计数 = sign(label)*count；
- 物理中央切片 M/E/S：轴由 SLICE_TOKENS 给出，层坐标 = 0，方向同正轴面。

同一轴上的所有转动互相交换（它们都是绕该轴的旋转），故可把**连续同轴**动作的
每层计数累加后再分解；不同轴的动作不交换，必须保持原顺序（作为折叠边界）。

分解规则（轴 a，正/负面 p/n，maxc=(n-1)d/2）：
    正面外层      T[maxc]      = outer + wide2
    正面宽二层    T[maxc-d]    = wide2
    负面外层      T[-maxc]     = -(outer_neg + wide2_neg)
    负面宽二层    T[-(maxc-d)] = -wide2_neg
    中央切片      T[0]         = slice

不认识的 token（如整体转动 x/y/z）作为边界原样保留，不跨其折叠。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from cube.coordinates import FACE_AXIS_SIGN, layer_values
from cube.middle_slice import SLICE_TOKENS
from cube.notation import parse_move_full

_AXIS_INDEX = {"x": 0, "y": 1, "z": 2}
_POS_FACE = ("R", "U", "F")
_NEG_FACE = ("L", "D", "B")
_SLICE_FACE = ("M", "E", "S")

Contrib = List[Tuple[int, int]]  # [(层坐标, 带符号计数)]


def _suffix(count: int) -> str:
    return {1: "", 2: "2", 3: "'"}[count]


def _token(face: str, layers: int, count: int) -> str:
    prefix = "" if layers == 1 else str(layers)
    return prefix + face + _suffix(count)


def _parse_physical(move: str, n: int) -> Optional[Tuple[int, Contrib]]:
    """解析单动作 -> (轴, [(层坐标, 带符号计数)])；非物理层动作返回 None。"""
    if move and move[0] in SLICE_TOKENS:
        axis_letter = SLICE_TOKENS[move[0]]
        turns = {"": 1, "'": 3, "2": 2}.get(move[1:], 0)
        if turns == 0:
            raise ValueError(f"非法切片后缀: {move!r}")
        return _AXIS_INDEX[axis_letter], [(0, turns)]
    try:
        label, layers, count = parse_move_full(move)
    except ValueError:
        return None
    if label in ("x", "y", "z"):
        return None
    axis, sign = FACE_AXIS_SIGN[label]
    coords = layer_values(n, label, layers=layers)
    return axis, [(c, sign * count) for c in coords]


def _emit_axis(n: int, axis: int, turns: Dict[int, int]) -> List[str]:
    pos = layer_values(n, _POS_FACE[axis], layers=2)
    neg = layer_values(n, _NEG_FACE[axis], layers=2)
    out: List[str] = []
    if len(pos) >= 2:
        wide2 = turns.get(pos[1], 0) % 4
        outer = (turns.get(pos[0], 0) - wide2) % 4
        if outer:
            out.append(_token(_POS_FACE[axis], 1, outer))
        if wide2:
            out.append(_token(_POS_FACE[axis], 2, wide2))
    else:
        outer = turns.get(pos[0], 0) % 4
        if outer:
            out.append(_token(_POS_FACE[axis], 1, outer))
    if len(neg) >= 2:
        wide2n = (-turns.get(neg[1], 0)) % 4
        outern = (turns.get(neg[1], 0) - turns.get(neg[0], 0)) % 4
        if outern:
            out.append(_token(_NEG_FACE[axis], 1, outern))
        if wide2n:
            out.append(_token(_NEG_FACE[axis], 2, wide2n))
    else:
        outern = (-turns.get(neg[0], 0)) % 4
        if outern:
            out.append(_token(_NEG_FACE[axis], 1, outern))
    mid = turns.get(0, 0) % 4
    if mid:
        out.append(_SLICE_FACE[axis] + _suffix(mid))
    return out


def _simplify_once(moves: List[str], n: int) -> List[str]:
    out: List[str] = []
    cur_axis: Optional[int] = None
    acc: Dict[int, int] = {}

    def flush() -> None:
        nonlocal cur_axis, acc
        if cur_axis is not None:
            out.extend(_emit_axis(n, cur_axis, acc))
        cur_axis = None
        acc = {}

    for mv in moves:
        parsed = _parse_physical(mv, n)
        if parsed is None:
            flush()
            out.append(mv)
            continue
        axis, contrib = parsed
        if axis != cur_axis:
            flush()
            cur_axis = axis
            acc = {}
        for coord, delta in contrib:
            acc[coord] = (acc.get(coord, 0) + delta) % 4
    flush()
    return out


def simplify_moves(moves: List[str], n: int = 5, max_passes: int = 8) -> List[str]:
    """返回与输入等价、且已折叠连续同轴动作的最短动作串（迭代至不动点）。

    单趟折叠会漏掉「中间同轴段整体抵消后两侧同轴段合并」的情形
    （如 `R U U' R'` -> `R R'` -> 空），故反复折叠直到不再变化。
    """
    cur = list(moves)
    for _ in range(max_passes):
        nxt = _simplify_once(cur, n)
        if nxt == cur:
            return nxt
        cur = nxt
    return cur


def simplify_verified(cube, moves: List[str], n: int = 5) -> List[str]:
    """化简并校验：化简前后在 `cube` 上重放得到相同状态，否则抛 AssertionError。"""
    simplified = simplify_moves(moves, n)
    a = cube.clone()
    a.apply_moves(list(moves))
    b = cube.clone()
    b.apply_moves(simplified)
    if a.cubies.keys() != b.cubies.keys():
        raise AssertionError("化简改变了块位置集合")
    for pos in a.cubies:
        ca, cb = a.cubies[pos], b.cubies[pos]
        if ca.home != cb.home or ca.stickers != cb.stickers:
            raise AssertionError("化简前后状态不一致 @ %s" % (pos,))
    return simplified
