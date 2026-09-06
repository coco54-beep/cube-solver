"""中心闭环宏可行性挖掘实验（Milestone 2.5a，精炼版）。

只关注「真正有用」的中心闭环宏：
  - color_off 起点=0 且终点=0（中心闭环）
  - 固定面心保持
  - 12 条逻辑棱全部保持配对（work_paired 全真）
  - 对棱产生「非恒等」置换（排除 4 转一圈这类恒等假象）

用有界 DFS（节点预算 + 深度上限）；对长序列只做去重采样。只做研究。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cube.cube5 import Cube5

from solver.edge5.compact_state import (
    MOVES,
    color_off,
    state_of,
    step,
    work_paired,
)
from solver.edge5.positions import SLOT_NAMES


def _edge_signature(st):
    """中/翼置换的紧凑签名（用于判断是否非恒等）."""
    # 把 middle+wing 拼成元组
    return (st.middle, st.wing)


def _search(max_depth, node_budget):
    start = state_of(Cube5.solved())
    wide_moves = [mv for mv in MOVES if mv[:1].isdigit()]
    results = []
    seen_sig = set()
    nodes = [0]

    def rec(st, path, depth):
        if nodes[0] >= node_budget or depth >= max_depth:
            return
        for mv in MOVES:
            nodes[0] += 1
            if nodes[0] >= node_budget:
                return
            # 禁止立即逆
            if path:
                last = path[-1]
                if (mv.lstrip("0123456789")[0] == last.lstrip("0123456789")[0]
                        and mv[:1].isdigit() == last[:1].isdigit()
                        and ((mv.endswith("'")) != (last.endswith("'")))):
                    continue
            ns = step(st, mv)
            np = path + (mv,)
            if color_off(ns) == 0 and any(m in wide_moves for m in np):
                # 检查所有槽保持配对
                st_ns = ns
                all_paired = all(work_paired(st_ns, n) for n in SLOT_NAMES)
                if all_paired:
                    sig = _edge_signature(st_ns)
                    start_sig = _edge_signature(start)
                    if sig != start_sig:
                        # 非恒等的、保持配对、中心闭环的宏
                        key = (len(np), sig)
                        if key not in seen_sig:
                            seen_sig.add(key)
                            results.append((np, sig))
            rec(ns, np, depth + 1)

    rec(start, (), 0)
    return results


def main():
    max_depth = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 60000
    results = _search(max_depth, budget)
    print(f"max_depth={max_depth} budget={budget} "
          f"unique_nontrivial_center_closed_preserving={len(results)}")

    from collections import Counter
    dc = Counter(len(p) for p, _ in results)
    print("长度分布:", dict(sorted(dc.items())))

    shown = 0
    seen_key = set()
    for path, sig in sorted(results, key=lambda r: len(r[0])):
        key = " ".join(path)
        if key in seen_key:
            continue
        seen_key.add(key)
        # 给出其对某条棱（UF）3 个成员所到槽的影响
        c = Cube5.solved()
        c.apply_moves(list(path))
        st_after = state_of(c)
        from solver.edge5.compact_state import target_home_slot, matched
        # 打印 UF 目标棱（若在 solved 里 it's the UF pair) 的成员槽
        print(f"  d={len(path)} moves={key}")
        shown += 1
        if shown >= 20:
            break


if __name__ == "__main__":
    main()
