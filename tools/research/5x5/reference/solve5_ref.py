"""5x5 端到端参考求解器（Plan 12）：中心 → 末段棱降阶 → 虚拟 3x3 → 回放。

串起已冻结/已验证的组件：
1. `solver.center5.solve_centers5` —— 中心归面（冻结库）。
2. `reduce5.reduce_edges` —— 配翼 + 末段降阶（6/6 fixtures 已实证到 all-complete）。
3. `solver.reduction.reduced_cube5.build_reduced_facelets` + `solver.solver3.solve_3x3`
   —— 构造虚拟 3x3 并用 hkociemba 求解。
4. 回放：整条序列用 `macro_effect.apply_token` 施加（支持 M/E/S 物理切片），
   最终断言 `cube.is_solved()`。

仅用于研究 oracle；不依赖 solver/edge5 的搜索类。
"""
from __future__ import annotations

import os
import random
import sys
from typing import Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import reduce5 as r5  # noqa: E402
import middle_orient_fix as mof  # noqa: E402
from reduce5 import me  # noqa: E402

from cube.cube5 import Cube5  # noqa: E402
from solver.center5 import solve_centers5  # noqa: E402
from solver.edge5.state import centers_are_color_solved, center_color_off  # noqa: E402
from solver.reduction.reduced_cube5 import build_reduced_facelets  # noqa: E402
from solver.solver3 import solve_3x3  # noqa: E402


def solve5_ref(cube: Cube5, iters: int = 1500000) -> Tuple[Optional[List[str]], Dict]:
    """从任意 5x5 状态求完整解；成功返回 (moves, info)，失败 (None, info)。"""
    work = cube.clone()
    moves: List[str] = []
    info: Dict = {}

    if not centers_are_color_solved(work):
        cr = solve_centers5(work)
        if not cr.success:
            info["stage"] = "centers"
            info["error"] = cr.message
            return None, info
        me.apply_macro(work, cr.moves)
        moves.extend(cr.moves)
        info["center_moves"] = len(cr.moves)
        if not centers_are_color_solved(work):
            info["stage"] = "centers"
            info["error"] = "中心求解后校验失败"
            return None, info
    else:
        info["center_moves"] = 0

    emoves, einfo = r5.reduce_edges(work, iters=iters)
    info["edges"] = {k: einfo.get(k) for k in
                     ("pair_moves", "xor", "parity_fix", "complete", "center_off", "fixed")}
    if emoves is None:
        info["stage"] = "edges"
        info["error"] = einfo.get("note", "末段降阶失败")
        return None, info
    me.apply_macro(work, emoves)
    moves.extend(emoves)

    fix_moves, finfo = mof.fix_middle_orientation(work)
    info["orient"] = finfo
    if fix_moves is None:
        info["stage"] = "orient"
        info["error"] = finfo.get("error", "中棱朝向修正失败")
        return None, info
    if fix_moves:
        me.apply_macro(work, fix_moves)
        moves.extend(fix_moves)
    info["orient_moves"] = len(fix_moves)

    facelets = build_reduced_facelets(work)
    r3 = solve_3x3(facelets)
    if not r3.success:
        info["stage"] = "reduce_3x3"
        info["error"] = r3.message
        return None, info
    work.apply_moves(r3.moves)
    moves.extend(r3.moves)

    info["edge_moves"] = len(emoves)
    info["moves3"] = len(r3.moves)
    info["total_moves"] = len(moves)
    info["solved"] = work.is_solved()
    info["center_off"] = center_color_off(work)
    return moves, info


def _random_scramble(cube: Cube5, n: int, rng: random.Random) -> List[str]:
    faces = ["U", "D", "L", "R", "F", "B"]
    suffixes = ["", "'", "2"]
    wide = ["2U", "2D", "2L", "2R", "2F", "2B"]
    seq = []
    last = None
    for _ in range(n):
        if rng.random() < 0.4:
            base = rng.choice(wide)
        else:
            base = rng.choice(faces)
        mv = base + rng.choice(suffixes)
        if last is not None and mv[0] == last[0]:
            continue
        last = mv
        seq.append(mv)
    for mv in seq:
        cube.apply_move(mv)
    return seq


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rng = random.Random(20260908)
    for i in range(5):
        c = Cube5.solved()
        scr = _random_scramble(c, 40, rng)
        moves, info = solve5_ref(c)
        if moves is None:
            print("scramble#%d FAIL %s" % (i, info), flush=True)
            continue
        check = c.clone()
        me.apply_macro(check, moves)
        print("scramble#%d solved=%s total=%d (center=%s edge=%s orient=%s 3x3=%s) "
              "edge_xor=%s v3_ok=%s" % (
                  i, check.is_solved(), info["total_moves"], info["center_moves"],
                  info["edge_moves"], info.get("orient_moves", 0), info["moves3"],
                  info["edges"]["xor"], info["solved"]), flush=True)
