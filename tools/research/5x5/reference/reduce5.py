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
import sys
from typing import Dict, List, Optional, Tuple

_REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
_REF = os.path.dirname(os.path.abspath(__file__))
for _p in (_REPO, _REF):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _load(name: str, path: str):
    if name in sys.modules and sys.modules[name] is not None:
        return sys.modules[name]
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ts = _load("ts", os.path.join(_REF, "terminal_state.py"))
p5 = _load("p5", os.path.join(_REF, "pairing5.py"))
me = _load("me", os.path.join(_REF, "macro_effect.py"))
ml = _load("ml", os.path.join(_REF, "macro_lib.py"))
ms = _load("ms", os.path.join(_REF, "terminal_solver.py"))

from cube.cube5 import Cube5  # noqa: E402

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
    return all(state[i] == state[N + i] for i in range(N))


def _mismatch(state: Tuple[int, ...]) -> int:
    return sum(1 for i in range(N) if state[i] != state[N + i])


def solve_all_complete(state: Tuple[int, ...], gens: Optional[List[ms.Macro]] = None,
                       iters: int = 1500000) -> Optional[List[ms.Macro]]:
    """A* 求宏序列使每槽中棱归属 == 翼对归属（all complete）。失败返回 None。"""
    if gens is None:
        gens = generators()
    if _all_complete(state):
        return []
    heap = []
    heapq.heappush(heap, (_mismatch(state), 0, state, []))
    seen = {state}
    while heap and len(seen) < iters:
        _f, _c, cur, path = heapq.heappop(heap)
        if _all_complete(cur):
            return path
        for m in gens:
            ns = ms.apply_macro_to_state(cur, m.mid_map, m.wing_map)
            if ns in seen:
                continue
            seen.add(ns)
            g = len(path) + 1
            heapq.heappush(heap, (g + _mismatch(ns), g, ns, path + [m]))
    return None


def _abstract_of(cube: Cube5) -> Tuple[int, ...]:
    return ms.abstract_state(cube)


def reduce_edges(cube: Cube5, iters: int = 1500000) -> Tuple[Optional[List[str]], Dict]:
    """对（中心已归面的）5x5 执行末段棱降阶，返回 (动作序列, 信息)。

    信息 dict 含 paired/mid_par/wing_par/xor/parity_fix/complete/center_off/fixed。
    """
    work = cube.clone()
    info: Dict = {}

    # 1) 配翼
    pair_moves = p5.solve_wing_pairs(work)
    work.apply_moves(pair_moves)
    info["pair_moves"] = len(pair_moves)

    # 2) 抽象状态与 XOR 不变量
    st = _abstract_of(work)
    mid_par = perm_sign(list(st[:N]))
    wing_par = perm_sign(list(st[N:]))
    xor = 0 if mid_par == wing_par else 1
    info.update(mid_par=mid_par, wing_par=wing_par, xor=xor)

    prefix: List[str] = []
    if xor == 1:
        # 用奇左翼宏打破配对，再重配 → 翻转 XOR
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
                prefix = list(seq) + list(rp)
                st = st2
                info["parity_fix"] = list(seq)
                info["repair_moves"] = len(rp)
                fixed = True
                break
        if not fixed:
            info["complete"] = False
            info["note"] = "no lw-odd parity macro flipped XOR"
            return None, info
    else:
        info["parity_fix"] = None

    # 3) A* 到 all-complete
    plan = solve_all_complete(st, iters=iters)
    if plan is None:
        info["complete"] = False
        info["note"] = "A* could not reach all-complete"
        return None, info
    for m in plan:
        me.apply_macro(work, m.seq)
    info["macro_moves"] = sum(len(m.seq) for m in plan)
    info["macro_count"] = len(plan)

    # 4) 断言
    info["complete"] = all(ts.is_complete_tredge(work, n) for n in ts.SLOT_NAMES)
    from solver.edge5.state import center_color_off
    from solver.edge5.free_slice import _fixed_centers_preserved
    info["center_off"] = center_color_off(work)
    info["fixed"] = _fixed_centers_preserved(work)

    moves = list(pair_moves) + prefix
    for m in plan:
        moves.extend(m.seq)
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

    gate = os.path.join(_REPO, "tests", "fixtures", "edge5", "gate5b")

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
