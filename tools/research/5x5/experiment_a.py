"""实验A：单翼可控插入（基于受控分散态）。

受控态构造：
  - 目标中棱固定在工作槽（UF）
  - 目标棱的一个翼放到入口位置 e（FR/FL 一带）
  - 另一个翼忽略（home）
  - 中心身份一致（center color_off==0）

枚举 W + outer^(1..N) + W'，找「关系等级净提升 且 中心最终归面」的宏。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from solver.edge5.free_slice import enumerate_wide_outer_wide_compact, edge_relation
from solver.edge5.compact_state import (
    CompactPairingState,
    _SLOT_WINGS,
    WING_INDEX,
    WING_ORDER,
)
from solver.edge5.compact_state import _SLOT_MID

# 入口候选：FR/FL 一带的翼坐标（两个 ±6，一个 ±3）
ENTRY_CANDIDATES = [
    (6, 3, 6), (6, -3, 6), (-6, 3, 6), (-6, -3, 6),   # FR / FL 两翼
    (6, 3, -6), (-6, 3, -6),                          # 其它近带
]


def controlled_start(target_home_slot: str, entry_pos) -> CompactPairingState:
    """构造受控分散态：目标中棱在 home，目标翼-a 移到 entry_pos，中心一致。"""
    mid = tuple(range(12))
    wing = list(range(24))
    # 目标翼 a 的 home 下标
    wa_home = _SLOT_WINGS[target_home_slot][0]
    e_idx = WING_INDEX[entry_pos]
    # 交换位置 wa_home 与 e_idx 的内容（把翼-a 塞到 entry，原 entry 块带回）
    wing[wa_home], wing[e_idx] = wing[e_idx], wing[wa_home]
    cen = tuple(range(54))
    return CompactPairingState(tuple(mid), tuple(wing), cen)


def main():
    slot = sys.argv[1] if len(sys.argv) > 1 else "UF"
    max_outer = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    entry = tuple(int(v) for v in sys.argv[3].split(",")) if len(sys.argv) > 3 else (3, 3, 6)

    ctrl = controlled_start(slot, entry)
    print("target slot", slot, "entry", entry)
    print("control relation_before:", edge_relation(ctrl, slot).relation)
    results = enumerate_wide_outer_wide_compact(max_outer, slot, start=ctrl)
    good = [r for r in results if r[3] and r[2] == 0]
    good.sort(key=lambda r: (len(r[0]), -r[1]))
    print(f"macro_count={len(results)}  gain_and_center_solved={len(good)}")
    for seq, rel, co, _ in good[:30]:
        print(f"  rel_before->after rel={rel}  co={co}  {' '.join(seq)}")


if __name__ == "__main__":
    main()
