"""5x5 求解器（降阶还原法：中心还原 → 三块棱配对 → 降阶 3x3 → 回放）。

管线（stages）：
1. solve_centers5   —— 中心按颜色归面（冻结的中心求解库）。
2. pair_all_edges   —— 12 条逻辑棱（每条 1 中棱 + 2 翼）各自聚拢配对。
3. build_reduced_facelets —— 把「中心归面 + 12 条配齐」的 5x5 折叠为 3x3 facelet。
4. solve_3x3        —— hkociemba 两阶段求解该 3x3。
5. 回放 —— 3x3 的 URFDLB 外层动作（与 5x5 同名外层等效）直接施加到 5x5。

配棱阶段使用单调收敛的贪心（每次只接受「配对槽数净增」的结果）。对任意深度打乱，
当前配棱器可能无法配齐全部 12 条；此时返回结构化失败（EDGE_PAIRING_INCOMPLETE），
而不是输出一个未完成/错误的解法。
"""

from typing import Dict, List

from cube.cube5 import Cube5
from solver.result import SolveResult, SolveStage

from solver.center5 import solve_centers5
from solver.edge5.state import centers_are_color_solved, paired_count
from solver.edge5.pairing_runner import pair_all_edges
from solver.reduction.reduced_cube5 import build_reduced_facelets
from solver.solver3 import solve_3x3


def _replay(cube: Cube5, moves) -> None:
    for mv in moves:
        cube.apply_move(mv)


def solve_5x5(cube: Cube5, cancel_event=None, progress_callback=None) -> SolveResult:
    """求解 5x5。返回 SolveResult（moves 为全部阶段动作的拼接）。"""
    if cube is None:
        return SolveResult(False, [], "cube 为 None", 0, 0,
                           [SolveStage("not_implemented", "cube 为 None")])
    work = cube.clone()
    all_moves: List[str] = []

    # ---- stage 1: 中心还原（仅当中心颜色未归面时才求解，避免无谓拆棱）----
    center_moves: List[str] = []
    center_msg = ""
    if centers_are_color_solved(work):
        center_msg = "中心颜色已归面，跳过"
    else:
        cr = solve_centers5(work)
        if not cr.success:
            return SolveResult(False, [], "中心还原失败: %s" % cr.message, 0, 0,
                               [SolveStage("solve_centers5", cr.message, list(cr.moves))])
        _replay(work, cr.moves)
        all_moves.extend(cr.moves)
        center_moves = list(cr.moves)
        center_msg = cr.message
        if not centers_are_color_solved(work):
            return SolveResult(False, [], "中心还原后校验失败", 0, len(all_moves),
                               [SolveStage("solve_centers5", cr.message, list(cr.moves))])

    # ---- stage 2: 棱配对（仅当未全部配对时才求解）----
    pr = pair_all_edges(work)
    _replay(work, pr.moves)
    all_moves.extend(pr.moves)
    if not pr.success:
        return SolveResult(
            False, all_moves, pr.message, 0, len(all_moves),
            [SolveStage("center", center_msg, center_moves),
             SolveStage("pair_edges", pr.message, list(pr.moves))],
        )

    # ---- stage 3: 降阶 3x3 ----
    facelets = build_reduced_facelets(work)
    r3 = solve_3x3(facelets)
    if not r3.success:
        return SolveResult(False, all_moves, "降阶 3x3 求解失败: %s" % r3.message,
                           0, len(all_moves),
                           [SolveStage("center", center_msg, center_moves),
                            SolveStage("pair_edges", "配齐 12 条", list(pr.moves))])

    # ---- stage 4: 回放 3x3 动作到 5x5 ----
    _replay(work, r3.moves)
    all_moves.extend(r3.moves)
    solved = work.is_solved()

    return SolveResult(
        solved, all_moves,
        "%s，共 %d 步（中心 %d + 配棱 %d + 3x3 %d）" % (
            "已还原" if solved else "回放校验未完全还原",
            len(all_moves), len(center_moves), len(pr.moves), len(r3.moves)
        ),
        0, len(all_moves),
        [SolveStage("center", center_msg, center_moves),
         SolveStage("pair_edges", "配齐 12 条", list(pr.moves)),
         SolveStage("reduce_3x3", "降阶求解", list(r3.moves))],
    )


def solve_5x5_facelets(
    facelets: Dict[str, List[List[str]]],
    cancel_event=None,
    progress_callback=None,
) -> SolveResult:
    """从 facelets 字典求解 5x5（构造 Cube5 后走 solve_5x5）。"""
    from cube.conversion import facelets_to_cubies
    cubies = facelets_to_cubies(facelets)
    cube = Cube5(cubies)
    return solve_5x5(cube, cancel_event=cancel_event, progress_callback=progress_callback)
