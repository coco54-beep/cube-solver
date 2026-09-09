"""5x5 末段棱降阶参考求解器（reference oracle，Plan 5–12 落地）。

输入：已完成中心归面的 5x5（本模块自带配翼，故也可直接接打乱态）。
输出：使「12 条 tredge 全部 complete + 中心归面 + 固定面心不动 + 虚拟 3x3 合法」
      的动作序列。

核心结论（见 TERMINAL_FINDINGS.md）：
- 末段真正判据 = 「归属全对/complete + 虚拟 3x3 合法」，**不要求**每条 tredge
  朝向正确（FLIPPED 若为偶数，虚拟 3x3 仍合法可解）。
- 抽象状态 = 每槽 (中棱归属, 翼对归属)。保持「翼对已配对」的生成元为
  整体搬运 3-cycle（transport）、纯净中棱 3-cycle（mid）、整体搬槽 4-cycle（外层转）。
  它们保持不变量 parity(mid) XOR parity(wing)。
- XOR=0 的 fixture 用上述生成元 A* 直达 all-complete。
- XOR=1 的 fixture 先用「奇左翼 2-cycle 宏」打破配对，再重新配翼（重配会翻转 XOR），
  之后同上。

仅用于研究 oracle；不依赖 solver/edge5 的搜索类。
"""
from __future__ import annotations

import heapq
import os
import random
import sys
from operator import eq, ne
from typing import Dict, List, Optional, Tuple

from cube.cube5 import Cube5

from . import terminal_state as ts
from . import pairing5 as p5
from . import macro_effect as me
from . import macro_lib as ml
from . import terminal_solver as ms

N = 12
_OUTER_TURNS = ["U", "U'", "U2", "R", "R'", "R2", "F", "F'", "F2",
                "D", "D'", "D2", "L", "L'", "L2", "B", "B'", "B2"]

# 已验证的「奇左翼 2-cycle」parity 宏（换位子形式 `2R B'L'B 2R' B'LB`）。
# 逐条实测：在复原态重放后 center_color_off==0 且 fixed_centers_ok，中棱不动。
# 由 joint_solver.collect_lw_odd_parity() 得到（45 条），此处取前 3 条。
_LW_ODD_MACROS: List[List[str]] = [
    ["2R", "B'", "L'", "B", "2R'", "B'", "L", "B"],
    ["2R'", "B'", "L'", "B", "2R", "B'", "L", "B"],
    ["2L", "F'", "R'", "F", "2L'", "F'", "R", "F"],
]

# OLL parity：单条 dedge 内部翻转（`d` 掩码奇偶位翻转），保持 tredge 配对与中心同色。
# 在复原态重放后 all-complete 且 center_color_off==0、fixed_centers_ok、d==1（仅翻转槽 0）。
# 用于消除「偶翻掩码库无法覆盖的奇 d」——同色中心解产生的棱态常落入此奇偶类。
_OLL_PARITY: List[str] = ["r2", "B2", "U2", "l", "U2", "r'", "U2", "r", "U2",
                          "F2", "r", "F2", "l'", "B2", "r2"]


def perm_sign(perm: List[int]) -> int:
    """置换的符号：+1 偶，-1 奇。"""
    seen = [False] * len(perm)
    s = 1
    for i in range(len(perm)):
        if not seen[i]:
            j, cyc = i, 0
            while not seen[j]:
                seen[j] = True
                j = perm[j]
                cyc += 1
            if cyc % 2 == 0:
                s = -s
    return s


def _outer_macros() -> List[ms.Macro]:
    out, seen = [], set()
    for mv in _OUTER_TURNS:
        eff = me.compute_effect([mv])
        if not (eff.centers_ok and eff.fixed_centers_ok and eff.moves_whole_slots()):
            continue
        mid_map = ms._map_from_perm(eff.middle_perm)
        wing_map = ms._map_from_perm(eff.left_wing_perm)
        key = (tuple(mid_map), tuple(wing_map))
        if key in seen:
            continue
        seen.add(key)
        out.append(ms.Macro("OUT:" + mv, [mv], mid_map, wing_map,
                            list(range(N)), list(range(N))))
    return out


_GENS: Optional[List[ms.Macro]] = None


def generators() -> List[ms.Macro]:
    """保持「翼对已配对」的生成元：transport 3-cycle + 中棱 3-cycle + 外层 4-cycle。"""
    global _GENS
    if _GENS is None:
        macros = ms.build_all_macros()
        trans = [m for m in macros if tuple(m.mid_map) == tuple(m.wing_map)]
        mid_only = [m for m in macros if tuple(m.wing_map) == tuple(range(N))]
        _GENS = trans + mid_only + _outer_macros()
    return _GENS


def _all_complete(state: Tuple[int, ...]) -> bool:
    return all(map(eq, state[:N], state[N:]))


def _mismatch(state: Tuple[int, ...]) -> int:
    return sum(map(ne, state[:N], state[N:]))


def solve_all_complete(state: Tuple[int, ...], gens: Optional[List[ms.Macro]] = None,
                       iters: int = 60000) -> Optional[List[ms.Macro]]:
    """A* 求宏序列使每槽中棱归属 == 翼对归属（all complete）。失败返回 None。"""
    cands = solve_all_complete_candidates(state, gens, max_candidates=1, iters=iters)
    return cands[0] if cands else None


def solve_all_complete_candidates(
    state: Tuple[int, ...],
    gens: Optional[List[ms.Macro]] = None,
    max_candidates: int = 6,
    iters: int = 60000,
    max_pops: int = 200000,
) -> List[List[ms.Macro]]:
    """A* 收集至多 max_candidates 个 all-complete 宏序列。

    搜索排序用「深度 + 错配数」（深度代价，规模可控；实测首个目标 ~11 次弹出）。
    真实展开成本（各宏 `len(seq)` 之和）不用于排序，而由调用方对候选逐一
    评分后取最优——直接在 293 宏空间上按真实成本排序会指数级爆炸。
    """
    if gens is None:
        gens = generators()
    if _all_complete(state):
        return [[]]
    counter = 0
    heap = [(_mismatch(state), 0, counter, state, ())]
    seen = {state}
    goals: List[List[ms.Macro]] = []
    pops = 0
    while heap and len(seen) < iters and pops < max_pops and len(goals) < max_candidates:
        _f, depth, _tie, cur, path = heapq.heappop(heap)
        pops += 1
        if _all_complete(cur):
            goals.append(list(path))
            continue
        for m in gens:
            ns = m.apply(cur)
            if ns in seen:
                continue
            seen.add(ns)
            counter += 1
            heapq.heappush(heap, (depth + 1 + _mismatch(ns), depth + 1,
                                  counter, ns, path + (m,)))
    return goals


def _abstract_of(cube: Cube5) -> Tuple[int, ...]:
    return ms.abstract_state(cube)


def _pair_variant(cube: Cube5, rng: Optional[random.Random] = None,
                  topk: int = 4) -> Tuple[Cube5, List[str]]:
    """配翼一个变体；rng=None 时用确定性贪心（cands[0]），否则在前 topk 中随机选。"""
    work = cube.clone()
    log: List[str] = []
    for _ in range(60):
        if p5.edges_paired(work):
            break
        cands = p5._candidate_swaps(work, log)
        if not cands:
            break
        if rng is None:
            _g, _l, _s, setup, ypos, other = cands[0]
        else:
            k = min(topk, len(cands))
            _g, _l, _s, setup, ypos, other = cands[rng.randrange(k)]
        if not p5._swap_positions(work, ypos, other, log, setup=setup):
            break
        log[:] = p5._compress_log(log)
    return work, log


def _pair_variant_beam(cube: Cube5, beam_width: int = 6,
                       per_state: int = 6) -> Tuple[Cube5, List[str]]:
    """配翼束搜索变体（比贪心略短）；不修改输入。"""
    work = cube.clone()
    moves = p5.pair_edges_beam(cube, beam_width=beam_width, per_state=per_state)
    work.apply_moves(moves)
    return work, moves


def _xor_of(cube: Cube5) -> int:
    st = _abstract_of(cube)
    return 0 if perm_sign(list(st[:N])) == perm_sign(list(st[N:])) else 1


def _best_edge_plan(cube: Cube5, iters: int, max_candidates: int):
    """对（已配对且 XOR=0 的）cube 求最优末段宏计划。

    返回 (edge+orient 成本, plan, edge_cost, fix_cost) 或 None。
    对每个 all-complete 候选施加朝向修正并校验虚拟 3x3 合法性。
    """
    st = _abstract_of(cube)
    cands = solve_all_complete_candidates(
        st, max_candidates=max_candidates, iters=iters)
    if not cands:
        return None

    from . import middle_orient_fix as mof
    from solver.reduction.reduced_cube5 import build_reduced_facelets
    from solver.solver3 import verify_3x3

    patterns = mof._load_patterns()
    best = None
    for path in cands:
        trial = cube.clone()
        for m in path:
            me.apply_macro(trial, m.seq)
        d = mof.orient_mask(trial)
        words = mof.solve_mask(d, patterns)
        if words is None:
            continue
        fix_moves = [x for w in words for x in w]
        me.apply_macro(trial, fix_moves)
        try:
            ok, _msg = verify_3x3(build_reduced_facelets(trial))
        except Exception:
            ok = False
        if not ok:
            continue
        edge_cost = sum(len(m.seq) for m in path)
        total = edge_cost + len(fix_moves)
        if best is None or total < best[0]:
            best = (total, path, edge_cost, len(fix_moves))
    return best


def reduce_edges(cube: Cube5, iters: int = 60000, max_candidates: int = 20,
                 pair_variants: int = 10,
                 progress_callback=None) -> Tuple[Optional[List[str]], Dict]:
    """对（中心已归面的）5x5 执行末段棱降阶，返回 (动作序列, 信息)。

    生成 `pair_variants` 个配翼变体（首个为确定性贪心，其余为随机贪心）；
    每个变体消除 XOR 后求最优末段宏计划，按「配翼 + parity + 棱 + 朝向」总成本
    选最优。信息 dict 含 pair_moves/mid_par/wing_par/xor/parity_fix/complete/
    center_off/fixed。
    """
    from solver.edge5.state import center_color_off
    from solver.edge5.free_slice import _fixed_centers_preserved

    best_overall = None  # (total, prefix, plan, edge_cost, fix_cost, pair_len, info)
    variants = max(1, pair_variants) + 1
    for vi in range(variants):
        if progress_callback is not None:
            try:
                progress_callback({"variant": vi, "variants": variants})
            except Exception:
                pass
        if vi == pair_variants:
            work, pair_moves = _pair_variant_beam(cube)
        else:
            rng = None if vi == 0 else random.Random(0xC0FFEE + vi)
            work, pair_moves = _pair_variant(cube, rng)
        if not p5.edges_paired(work):
            continue

        info: Dict = {"pair_moves": len(pair_moves)}
        st = _abstract_of(work)
        mid_par = perm_sign(list(st[:N]))
        wing_par = perm_sign(list(st[N:]))
        xor = 0 if mid_par == wing_par else 1
        info.update(mid_par=mid_par, wing_par=wing_par, xor=xor)

        prefix: List[str] = list(pair_moves)
        if xor == 1:
            fixed = False
            for seq in _LW_ODD_MACROS:
                trial = work.clone()
                me.apply_macro(trial, seq)
                try:
                    rp = p5.solve_wing_pairs(trial)
                except ValueError:
                    continue
                trial.apply_moves(rp)
                st2 = _abstract_of(trial)
                if perm_sign(list(st2[:N])) == perm_sign(list(st2[N:])):
                    work = trial
                    prefix = list(pair_moves) + list(seq) + list(rp)
                    info["parity_fix"] = list(seq)
                    info["repair_moves"] = len(rp)
                    fixed = True
                    break
            if not fixed:
                continue
        else:
            info["parity_fix"] = None

        best = _best_edge_plan(work, iters, max_candidates)
        prefix_extra: List[str] = []
        if best is None:
            # 奇 d 掩码：先施加 OLL parity 翻转单条 dedge 奇偶位，再求末段计划。
            work_p = work.clone()
            work_p.apply_moves(list(_OLL_PARITY))
            best = _best_edge_plan(work_p, iters, max_candidates)
            if best is not None:
                prefix_extra = list(_OLL_PARITY)
        if best is None:
            continue
        edge_total, plan, edge_cost, fix_cost = best
        full_prefix = list(prefix) + prefix_extra
        total = len(full_prefix) + edge_total
        if best_overall is None or total < best_overall[0]:
            if prefix_extra:
                info["oll_parity"] = list(prefix_extra)
            best_overall = (total, full_prefix, plan, edge_cost, fix_cost,
                            len(pair_moves), info)

    if best_overall is None:
        return None, {"complete": False,
                      "note": "all pairing variants failed to reduce"}

    _total, prefix, plan, edge_cost, fix_cost, pair_len, info = best_overall

    # 用选中的前缀 + 计划在 base 上重建，供断言与返回。
    work = cube.clone()
    moves: List[str] = list(prefix)
    me.apply_macro(work, moves)
    for m in plan:
        me.apply_macro(work, m.seq)
        moves.extend(m.seq)

    info["pair_moves"] = pair_len
    info["macro_moves"] = edge_cost
    info["macro_count"] = len(plan)
    info["chosen_orient_cost"] = fix_cost
    info["complete"] = all(ts.is_complete_tredge(work, n) for n in ts.SLOT_NAMES)
    info["center_off"] = center_color_off(work)
    info["fixed"] = _fixed_centers_preserved(work)
    return moves, info


def virtual_3x3_legal(cube: Cube5) -> bool:
    """构造虚拟 3x3 并用 3x3 求解器判定合法性。"""
    from solver.reduction.reduced_cube5 import build_reduced_facelets
    from solver.solver3 import solve_3x3
    return bool(solve_3x3(build_reduced_facelets(cube)).success)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import json

    gate = os.path.join(os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")),
        "tests", "fixtures", "edge5", "gate5b")

    def fixture(name):
        with open(os.path.join(gate, name), encoding="utf-8") as f:
            fx = json.load(f)
        c = Cube5.solved()
        for k in ["scramble", "center_moves", "gate3_moves", "gate4_moves",
                  "setup_moves", "insert_moves"]:
            if k in fx:
                c.apply_moves(fx[k])
        return c

    names = ["flip_seed19.json", "flip_seed2.json", "flip_seed51.json",
             "flip_seed23.json", "flip_seed4.json", "flip_seed7.json"]
    for name in names:
        c = fixture(name)
        moves, info = reduce_edges(c)
        if moves is None:
            print("%-18s FAIL %s" % (name, info))
            continue
        check = c.clone()
        me.apply_macro(check, moves)
        legal = virtual_3x3_legal(check)
        print("%-18s xor=%d complete=%s center_off=%d fixed=%s v3=%s "
              "moves=%d (pair=%d fix=%s)" % (
                  name, info["xor"], info["complete"], info["center_off"],
                  info["fixed"], legal, len(moves), info["pair_moves"],
                  "yes" if info.get("parity_fix") else "no"), flush=True)
