"""5x5 端到端参考管线（生产移植版）。

把已验证的 reference oracle 组件串成可在生产环境直接调用的求解流程：

1. `solver.center5.solve_centers5` —— 中心归面。
2. `reduce5.reduce_edges` —— 配翼 + 末段棱降阶（A* 宏级规划）。
3. `middle_orient_fix.fix_middle_orientation` —— 消除「中棱相对翼内部翻转」，
   使 tredge 内部朝向一致（否则虚拟 3x3 会掩盖该缺陷）。
4. `build_reduced_facelets` + `solve_3x3` —— 虚拟 3x3 求解。
5. 回放并断言 `cube.is_solved()`。

`apply_macro`（macro_effect）支持 M/E/S 物理切片 token，整条序列一次性施加。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from cube.cube5 import Cube5
from solver.center5 import solve_centers5
from solver.edge5.state import centers_are_color_solved, center_color_off
from solver.reduction.reduced_cube5 import build_reduced_facelets
from solver.solver3 import solve_3x3

from . import middle_orient_fix as mof
from . import reduce5 as r5
from .reduce5 import me

DEFAULT_EDGE_ITERS = 1500000


def reduce_after_centers(cube: Cube5, iters: int = DEFAULT_EDGE_ITERS) -> Tuple[Optional[List[str]], Dict]:
    """在「中心已归面」的 cube 上完成棱降阶与朝向修正（原地修改 cube）。

    返回 (moves, info)；失败时 moves=None，info 含 `stage`/`error`。
    """
    info: Dict = {}
    moves: List[str] = []

    emoves, einfo = r5.reduce_edges(cube, iters=iters)
    info["edges"] = {k: einfo.get(k) for k in
                     ("pair_moves", "xor", "parity_fix", "complete", "center_off", "fixed")}
    if emoves is None:
        info["stage"] = "edges"
        info["error"] = einfo.get("note", "末段降阶失败")
        return None, info
    me.apply_macro(cube, emoves)
    moves.extend(emoves)
    info["edge_moves"] = len(emoves)

    fix_moves, finfo = mof.fix_middle_orientation(cube)
    info["orient"] = finfo
    if fix_moves is None:
        info["stage"] = "orient"
        info["error"] = finfo.get("error", "中棱朝向修正失败")
        return None, info
    if fix_moves:
        me.apply_macro(cube, fix_moves)
        moves.extend(fix_moves)
    info["orient_moves"] = len(fix_moves)

    facelets = build_reduced_facelets(cube)
    r3 = solve_3x3(facelets)
    if not r3.success:
        info["stage"] = "reduce_3x3"
        info["error"] = r3.message
        return None, info
    cube.apply_moves(r3.moves)
    moves.extend(r3.moves)
    info["moves3"] = len(r3.moves)
    info["center_off"] = center_color_off(cube)
    info["solved"] = cube.is_solved()
    return moves, info


def solve5_ref(cube: Cube5, iters: int = DEFAULT_EDGE_ITERS) -> Tuple[Optional[List[str]], Dict]:
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

    emoves, einfo = reduce_after_centers(work, iters=iters)
    info.update(einfo)
    if emoves is None:
        return None, info
    moves.extend(emoves)

    info["total_moves"] = len(moves)
    info["solved"] = work.is_solved()
    return moves, info
