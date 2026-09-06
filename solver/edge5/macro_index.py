"""宏效果索引：去重 / 置换效果 / 兼容存储掩码 / 拆散掩码 / 倒排索引。

全部基于 compact 态从 identity 出发的纯置换效果，离线可算、与起始状态无关。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from solver.edge5.compact_state import CompactPairingState, MOVE_TABLES, MOVES, step, color_off
from solver.edge5.free_slice import (
    _slot_of_mid_idx, _slot_of_wing_idx, target_pieces, MIDDLE_ORDER, WING_ORDER,
)
from solver.edge5.positions import SLOT_NAMES

_IDENTITY = CompactPairingState(
    middle=tuple(range(12)),
    wing=tuple(range(24)),
    center=tuple(range(54)),
)

SLOT_INDEX = {name: i for i, name in enumerate(SLOT_NAMES)}

WIDE_QUARTER: Tuple[str, ...] = (
    "2U", "2U'", "2D", "2D'", "2L", "2L'", "2R", "2R'", "2F", "2F'", "2B", "2B'",
)
OUTER: Tuple[str, ...] = (
    "U", "U'", "U2", "D", "D'", "D2", "L", "L'", "L2",
    "R", "R'", "R2", "F", "F'", "F2", "B", "B'", "B2",
)


def _inv(mv: str) -> str:
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    return mv + "'"


def _same_face(a: str, b: str) -> bool:
    fa = a if a.isalpha() else a[1:]
    fb = b if b.isalpha() else b[1:]
    return fa == fb


def build_center_kept_macros(max_outer: int = 3) -> List[Tuple[str, ...]]:
    """枚举 W + outer^(1..max_outer) + W⁻¹，保留 center color_off==0 的中心保持宏。

    与研究对象一致（3480 个，depth≤3）。仅用 compact 态筛选，避免重放真实 Cube5。
    """
    from itertools import product
    out = []
    for wide in WIDE_QUARTER:
        close = _inv(wide)
        for n in range(1, max_outer + 1):
            for A in product(OUTER, repeat=n):
                bad = False
                for i in range(1, len(A)):
                    if _same_face(A[i - 1], A[i]):
                        bad = True
                        break
                if bad:
                    continue
                seq = (wide,) + A + (close,)
                st = apply_macro(_IDENTITY, seq)
                if color_off(st) == 0:
                    out.append(seq)
    return out


def build_macro_index(max_outer: int = 3) -> "MacroIndex":
    return MacroIndex(build_center_kept_macros(max_outer))


def apply_macro(state: CompactPairingState, moves: Tuple[str, ...]) -> CompactPairingState:
    s = state
    for mv in moves:
        s = step(s, mv)
    return s


@dataclass(frozen=True)
class MacroEffect:
    macro_id: int
    moves: Tuple[str, ...]
    middle_after: Tuple[int, ...]   # 位置 -> home 索引
    wing_after: Tuple[int, ...]
    # home -> 宏作用后落槽 (None=未定位)
    mid_dest: Dict[int, str]
    wing_dest: Dict[int, str]
    # 12-bit: bit i=1 表示「若完整组在槽 i，宏作用后仍三块同槽」(保配对)
    compatible_storage_mask: int
    # 12-bit: bit i=1 表示「宏会把槽 i 的完整组拆散」(=~compatible)
    split_slot_mask: int
    center_face_preserving: int  # center color_off 增量（宏本就中心保持，=0）
    effect_fingerprint: Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]
    touched_slot_mask: int
    length: int


def _dest_maps(state_after: CompactPairingState):
    mid = {}
    for h in range(12):
        mid[h] = _slot_of_mid_idx(state_after, h)
    wing = {}
    for h in range(24):
        wing[h] = _slot_of_wing_idx(state_after, h)
    return mid, wing


def _group_kept(mid_dst: str, wa_dst: str, wb_dst: str) -> bool:
    return mid_dst is not None and mid_dst == wa_dst and mid_dst == wb_dst


def compute_effect(macro_id: int, moves: Tuple[str, ...]) -> MacroEffect:
    st = apply_macro(_IDENTITY, moves)
    mid_dest, wing_dest = _dest_maps(st)

    compatible = 0
    touched = 0
    for i, name in enumerate(SLOT_NAMES):
        tp = target_pieces(name)
        md = mid_dest[tp.middle_home]
        wa = wing_dest[tp.wing_a_home]
        wb = wing_dest[tp.wing_b_home]
        if _group_kept(md, wa, wb):
            compatible |= (1 << i)
        # touched = 宏对槽 i 有任一块移动/影响
        if md is not None or wa is not None or wb is not None:
            # 粗略：宏改变了该槽三块中任一块的位置
            touched |= (1 << i)

    split = (~compatible) & ((1 << 12) - 1)
    fp = (st.middle, st.wing)   # 配棱效果去重键（center 单测 color_off）
    center_ok = 1 if color_off(st) == 0 else 0
    return MacroEffect(
        macro_id=macro_id,
        moves=moves,
        middle_after=st.middle,
        wing_after=st.wing,
        mid_dest=mid_dest,
        wing_dest=wing_dest,
        compatible_storage_mask=compatible,
        split_slot_mask=split,
        center_face_preserving=center_ok,
        effect_fingerprint=fp,
        touched_slot_mask=touched,
        length=len(moves),
    )


class MacroIndex:
    """对一组宏：去重（保留最优）、算效果、建倒排索引。"""

    def __init__(self, macro_list: List[Tuple[str, ...]]):
        # 1) 按效果去重
        best: Dict[Tuple, MacroEffect] = {}
        for i, mac in enumerate(macro_list):
            eff = compute_effect(i, mac)
            key = eff.effect_fingerprint
            if key not in best or _better(eff, best[key]):
                best[key] = eff

        self.effects: List[MacroEffect] = sorted(best.values(), key=lambda e: e.length)
        self.by_id = {e.macro_id: e for e in self.effects}
        self.by_fingerprint = {e.effect_fingerprint: e for e in self.effects}

        # 2) 倒排索引：compatible_storage_mask -> 宏列表
        self.by_compat_mask: Dict[int, List[MacroEffect]] = {}
        for e in self.effects:
            self.by_compat_mask.setdefault(e.compatible_storage_mask, []).append(e)

    def candidates_compatible(self, protected_slot_mask: int) -> List[MacroEffect]:
        """返回与 protected_slot_mask 兼容的宏（不拆任何保护槽）。"""
        out = []
        for e in self.effects:
            if (protected_slot_mask & ~e.compatible_storage_mask) == 0:
                out.append(e)
        return out

    def __len__(self):
        return len(self.effects)


def _better(a: MacroEffect, b: MacroEffect) -> bool:
    if a.length != b.length:
        return a.length < b.length
    # 同长度：触碰槽更少者优；再比 touched 掩码
    ta, tb = bin(a.touched_slot_mask).count('1'), bin(b.touched_slot_mask).count('1')
    if ta != tb:
        return ta < tb
    # 记号稳定：取 moves 字典序小者
    return a.moves < b.moves
