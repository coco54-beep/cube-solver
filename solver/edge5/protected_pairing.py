"""中心保持配棱主循环（slice-band 安全存储 + 保护兼容规划）。

流程：
1. 构建 MacroIndex（中心保持宏，去重后用于 gather/flip）。
2. 裸配第 1 条（从 0 保护组）：gather + flip，得到 ≥1 保护组。
3. 主循环：反复 `pair_one_protected`（store 保护组→safe + 兼容宏 gather + flip），
   逐步累积，中心全程归面、保护组全存活，直到无法净增至 12 条。

不修改传入 cube；返回 (after_cube, moves, 配对数, 完成与否)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from cube.cube5 import Cube5

from .macro_index import build_macro_index, MacroIndex
from .state import is_edge_paired, centers_are_color_solved, paired_count
from .free_slice import edge_relation
from .compact_state import state_of, step
from .positions import SLOT_NAMES
from .slice_band import BANDS
from .pairing_transaction import pair_one_protected, Gate2Result

DEFAULT_FIRST_TARGETS = ("UF", "UR", "UL", "UB", "DF", "DR", "DB", "DL")


def _gather_beam(st, target, macro_index, width=40, depth=3):
    frontier = [(st, [])]
    best = (st, [], edge_relation(st, target).relation)
    for _ in range(depth):
        cands = []
        for s, path in frontier:
            for e in macro_index.effects:
                s2 = s
                for mv in e.moves:
                    s2 = step(s2, mv)
                r = edge_relation(s2, target).relation
                if r > best[2]:
                    best = (s2, path + [e.moves], r)
                cands.append((s2, path + [e.moves], r))
        cands.sort(key=lambda t: -t[2])
        frontier = [(s, p) for s, p, r in cands[:width]]
        if not frontier:
            break
    return best


def _flip_fix(cube, target, macro_index):
    for e in macro_index.effects:
        if e.length > 5:
            continue
        x = cube.clone()
        for mv in e.moves:
            x.apply_move(mv)
        if centers_are_color_solved(x) and is_edge_paired(x, target):
            return e.moves
    return None


def _pair_first(cube, target, macro_index):
    st, path, r = _gather_beam(state_of(cube), target, macro_index)
    if r < 3:
        return None, ()
    w = cube.clone()
    moves = []
    for mac in path:
        for mv in mac:
            w.apply_move(mv)
            moves.append(mv)
    if not is_edge_paired(w, target):
        fx = _flip_fix(w, target, macro_index)
        if fx is None:
            return None, ()
        for mv in fx:
            w.apply_move(mv)
            moves.append(mv)
    return w, tuple(moves)


@dataclass
class PairAllResult:
    after: Cube5
    moves: Tuple[str, ...]
    paired: int
    completed: bool
    steps: int


def pair_all_protected(
    cube: Cube5,
    macro_index: Optional[MacroIndex] = None,
    first_targets=DEFAULT_FIRST_TARGETS,
    max_steps: int = 24,
) -> PairAllResult:
    if macro_index is None:
        macro_index = build_macro_index(3)

    w = cube.clone()
    all_moves = []
    steps = 0

    # 0) 中心必须已归面
    if not centers_are_color_solved(w):
        return PairAllResult(w, tuple(all_moves), paired_count(w), False, steps)

    # 1) 裸配第 1 条
    if paired_count(w) == 0:
        first = None
        for tgt in first_targets:
            x, mv = _pair_first(w, tgt, macro_index)
            if x is not None and paired_count(x) >= 1:
                first = (x, tgt, mv)
                break
        if first is None:
            return PairAllResult(w, tuple(all_moves), paired_count(w), False, steps)
        w = first[0]
        all_moves.extend(first[2])
        steps += 1

    # 2) 主循环
    while paired_count(w) < 12 and steps < max_steps:
        done = False
        for bname in BANDS:
            res = pair_one_protected(w, macro_index, bname)
            if res.gate2_success and res.after is not None:
                w = res.after
                all_moves.extend(res.moves)
                steps += 1
                done = True
                break
        if not done:
            break

    return PairAllResult(w, tuple(all_moves), paired_count(w), paired_count(w) >= 12, steps)
