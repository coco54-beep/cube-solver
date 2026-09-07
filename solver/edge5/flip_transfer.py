"""Gate 5b · 双棱「目标→缓冲」奇偶转移的数据模型。

Gate 5b 目标不是「凭空消除翻转」，而是**显式**把目标棱 A 的翻转缺陷转移给另一条
尚未配对的缓冲棱 B：

    A：FLIPPED -> VALID          （A 的三块最终成为完整可配对棱）
    B：允许被拆散 / 重排 / 接收翻转缺陷
    其它保护组：事务终点全部存活
    中心：事务终点归面；固定面心保持；真实重放一致

本模块只定义/构造该事务的**状态描述**（`FlipTransferState`）与缓冲棱的选取规则
（`choose_unpaired_buffer_edge`），不在此做修正公式搜索或公式适配。

关键认知（诚实）：
- 「朝向翻转」取**槽内相对测量**——中棱相对同槽两翼是否一致（见 `_orientation_consistent`），
  而非绝对 home 指派。因此 `target_orientation` / `buffer_orientation` 用「在哪个槽配齐时
  的 is_edge_paired 真假」来刻画（配齐但未配对 = 翻转待转移）。
- 单棱翻转在单 tredge 装配 + 中心保持宏空间内不可修正（经验边界，见 Gate 5 总结），
  故必须以双棱（带缓冲）方式转移；真正无缓冲的最后两棱奇偶留 Gate 7。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .compact_state import state_of, _SLOT_MID, _SLOT_WINGS
from .freeslice_layout import FreeSliceLayout, DEFAULT_LAYOUT, OUTER_MOVES
from .positions import (
    MIDDLE_ORDER, WING_ORDER, SLOT_NAMES, slot_of,
)
from .state import centers_are_color_solved, is_edge_paired
from .free_slice import _fixed_centers_preserved, _slot_of_mid_idx, _slot_of_wing_idx

Coord = Tuple[int, int, int]


def _mid_pos(cube, home_idx: int) -> Optional[Coord]:
    for cubie in cube.cubies.values():
        if cubie.home == MIDDLE_ORDER[home_idx]:
            return cubie.pos
    return None


def _wing_pos(cube, home_idx: int) -> Optional[Coord]:
    for cubie in cube.cubies.values():
        if cubie.home == WING_ORDER[home_idx]:
            return cubie.pos
    return None


def _logical_edge_current_slot(cube, slot_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """返回逻辑棱 home=`slot_name` 的三块此刻各自所在槽名。"""
    m = _SLOT_MID[slot_name]
    wa, wb = _SLOT_WINGS[slot_name]
    st = state_of(cube)
    return (_slot_of_mid_idx(st, m), _slot_of_wing_idx(st, wa), _slot_of_wing_idx(st, wb))


def _tredge_flipped_at(cube, home_slot: str) -> bool:
    """逻辑棱（home 槽=`home_slot`）的三块是否在某槽配齐但未配对（相对翻转）。

    **注意**：三块可能聚集在**非 home 槽**（如 DF 上的 UF 家棱被翻转），因此按
    「三块此刻共同的槽」而不是 home 槽判断。
    """
    ms, as_, bs_ = _logical_edge_current_slot(cube, home_slot)
    if ms is None or not (ms == as_ == bs_):
        return False
    return not is_edge_paired(cube, ms)


@dataclass(frozen=True)
class FlipTransferState:
    """一次 Gate 5b 双棱转移事务的端点状态描述。"""

    target_a_slot: str
    target_piece_positions: Tuple[Coord, Coord, Coord]
    target_orientation: int          # 1 = 待转移的翻转缺陷（配齐但仍未配对）
    buffer_b_slot: str
    buffer_piece_positions: Tuple[Coord, Coord, Coord]
    buffer_orientation: int          # 1 = 接收/携有翻转缺陷（允许）
    protected_slots: Tuple[str, ...]
    protected_signature: Tuple[bool, ...]   # 与 protected_slots 对应的「是否仍配对」
    center_signature: int                    # 中心错位数（0 = 归面）
    fixed_centers_preserved: bool
    centers_solved: bool

    @property
    def target_home_id(self) -> Tuple[int, int, int]:
        return (_SLOT_MID[self.target_a_slot],
                _SLOT_WINGS[self.target_a_slot][0],
                _SLOT_WINGS[self.target_a_slot][1])

    @property
    def buffer_home_id(self) -> Tuple[int, int, int]:
        return (_SLOT_MID[self.buffer_b_slot],
                _SLOT_WINGS[self.buffer_b_slot][0],
                _SLOT_WINGS[self.buffer_b_slot][1])


def compute_flip_transfer_state(
    cube,
    *,
    target_a_slot: str,
    buffer_b_slot: str,
    protected_slots: Tuple[str, ...] = (),
) -> FlipTransferState:
    """构造当前 cube 上「目标 A + 缓冲 B」事务的端点状态。只读。"""
    if target_a_slot == buffer_b_slot:
        raise ValueError("目标与缓冲不能为同一逻辑棱")
    if target_a_slot in protected_slots or buffer_b_slot in protected_slots:
        raise ValueError("目标/缓冲不可同时位于保护组内")
    mid_id, wa_id, wb_id = (_SLOT_MID[target_a_slot],
                            _SLOT_WINGS[target_a_slot][0],
                            _SLOT_WINGS[target_a_slot][1])
    bmid, bwa, bwb = (_SLOT_MID[buffer_b_slot],
                      _SLOT_WINGS[buffer_b_slot][0],
                      _SLOT_WINGS[buffer_b_slot][1])
    prot_sig = tuple(is_edge_paired(cube, s) for s in protected_slots)
    from .state import center_color_off
    return FlipTransferState(
        target_a_slot=target_a_slot,
        target_piece_positions=(_mid_pos(cube, mid_id), _wing_pos(cube, wa_id), _wing_pos(cube, wb_id)),
        target_orientation=1 if _tredge_flipped_at(cube, target_a_slot) else 0,
        buffer_b_slot=buffer_b_slot,
        buffer_piece_positions=(_mid_pos(cube, bmid), _wing_pos(cube, bwa), _wing_pos(cube, bwb)),
        buffer_orientation=1 if _tredge_flipped_at(cube, buffer_b_slot) else 0,
        protected_slots=tuple(protected_slots),
        protected_signature=prot_sig,
        center_signature=center_color_off(cube),
        fixed_centers_preserved=_fixed_centers_preserved(cube),
        centers_solved=centers_are_color_solved(cube),
    )


def choose_unpaired_buffer_edge(
    cube,
    *,
    target_a_slot: str,
    protected_slots: Tuple[str, ...] = (),
    fixed_buffer_slots: Tuple[str, ...] = ("UR", "UB"),
    max_depth: int = 8,
) -> Optional[str]:
    """选取一条尚未配对的缓冲棱 B 的 home 槽名。只读，确定性。

    规则：
    - 不是目标 A；不在保护组内；
    - 当前**不是**已配对（`is_edge_paired` 为假，即松散/未配，可接收翻转缺陷）；
    - 其「中棱 piece」可由纯外层搬到某个固定缓冲槽（`fixed_buffer_slots`），
      从而作为"固定缓冲"处理（规范化布局）。
    返回缓冲 home 槽名；无合适选择返回 None。
    """
    from .freeslice_layout import relocate_middle_to_pos
    from .positions import MIDDLE_INDEX, slot
    st = state_of(cube)
    targets = {MIDDLE_INDEX[slot(s).middle] for s in fixed_buffer_slots}
    for name in SLOT_NAMES:
        if name == target_a_slot or name in protected_slots:
            continue
        if is_edge_paired(cube, name):
            continue
        m_home = _SLOT_MID[name]
        mpos_idx = next((j for j, v in enumerate(st.middle) if v == m_home), None)
        if mpos_idx is None:
            continue
        for tpos in targets:
            if relocate_middle_to_pos(mpos_idx, tpos, max_depth) is not None:
                return name
    return None
