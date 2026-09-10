"""5x5 求解器（降阶还原法：中心还原 → 棱降阶 → 降阶 3x3 → 回放）。

管线（stages）：
1. solve_centers5   —— 中心按颜色归面（冻结的中心求解库）。
2. reduce_edges     —— reference ref5 管线：配翼 + 末段宏级 A* 规划，
                       使 12 条逻辑棱（每条 1 中棱 + 2 翼）全部 complete。
3. fix_middle_orientation —— 消除「中棱相对翼内部翻转」，使 tredge 内部朝向一致
                       （否则虚拟 3x3 会掩盖该缺陷、回放后仍不复原）。
4. build_reduced_facelets —— 把「中心归面 + 12 条配齐 + 朝向一致」的 5x5 折叠为 3x3。
5. solve_3x3        —— hkociemba 两阶段求解该 3x3。
6. 回放 —— 3x3 的 URFDLB 外层动作（与 5x5 同名外层等效）直接施加到 5x5。

棱降阶阶段使用已验证的 reference 宏级规划器（见 `solver/reduction/ref5/`）。
"""

from typing import Dict, List

from cube.cube5 import Cube5
from solver.result import SolveResult, SolveStage

from solver.center5 import solve_centers5, solve_centers5_color
from solver.center5.orbits import kind_of_position
from solver.edge5.state import centers_are_color_solved
from solver.reduction.ref5 import reduce5 as ref5_reduce
from solver.reduction.ref5 import middle_orient_fix as ref5_mof
from solver.reduction.ref5.reduce5 import me as ref5_me
from solver.reduction.ref5.simplify_moves import simplify_moves
from solver.reduction.reduced_cube5 import build_reduced_facelets
from solver.solver3 import solve_3x3


def _replay(cube: Cube5, moves) -> None:
    for mv in moves:
        cube.apply_move(mv)


def _emit(progress_callback, stage=None, progress=None, label=None) -> None:
    """向 UI 上报求解进度（后台线程调用；异常不得影响求解）。"""
    if progress_callback is None:
        return
    payload = {}
    if stage is not None:
        payload["stage"] = stage
    if progress is not None:
        payload["progress"] = progress
    if label is not None:
        payload["label"] = label
    try:
        progress_callback(payload)
    except Exception:
        pass


_SOLVED5: Cube5 = None


def _solved5() -> Cube5:
    global _SOLVED5
    if _SOLVED5 is None:
        _SOLVED5 = Cube5.solved()
    return _SOLVED5


def _center_cubies(cube: Cube5):
    return [(pos, cb) for pos, cb in cube.cubies.items() if len(cb.stickers) == 1]


def _center_homes_consistent(cube: Cube5) -> bool:
    """中心 home 是否可信：home 位置在复原态的贴纸颜色 == 当前贴纸颜色。"""
    solved = _solved5()
    for _pos, cb in _center_cubies(cube):
        scb = solved.cubies.get(cb.home)
        if scb is None or len(scb.stickers) != 1:
            return False
        (col,) = cb.stickers.values()
        if list(scb.stickers.values())[0] != col:
            return False
    return True


def _rebuild_center_homes(cube: Cube5) -> None:
    """为 5x5 中心按 (轨道, 颜色) 分桶赋予互异 home（facelets 重建的 cube 需要）。"""
    buckets = {}
    for pos, cb in _center_cubies(_solved5()):
        (col,) = cb.stickers.values()
        buckets.setdefault((kind_of_position(pos), col), []).append(pos)
    for k in buckets:
        buckets[k].sort()
    for pos, cb in _center_cubies(cube):
        (col,) = cb.stickers.values()
        cb.home = buckets[(kind_of_position(pos), col)].pop()


def _swap_two_center_homes(cube: Cube5) -> bool:
    """交换两个同 (轨道, 颜色) 中心的 home：翻转中心置换奇偶（用于修 odd-d）。"""
    groups = {}
    for pos, cb in _center_cubies(cube):
        (col,) = cb.stickers.values()
        groups.setdefault((kind_of_position(pos), col), []).append(cb)
    for g in groups.values():
        if len(g) >= 2:
            g[0].home, g[1].home = g[1].home, g[0].home
            return True
    return False


def solve_5x5(cube: Cube5, cancel_event=None, progress_callback=None) -> SolveResult:
    """求解 5x5。返回 SolveResult（moves 为全部阶段动作的拼接）。

    若中心 home 不可信（如由 facelets 重建、home==pos），先按颜色/轨道重建；
    首解失败时交换两个同色中心 home 再解一次（修正中棱朝向 GF(2) 奇偶）。
    """
    if cube is None:
        return SolveResult(False, [], "cube 为 None", 0, 0,
                           [SolveStage("not_implemented", "cube 为 None")])

    work = cube.clone()
    if not _center_homes_consistent(work):
        _rebuild_center_homes(work)

    result = _solve_once(work, cancel_event, progress_callback)
    if result.success:
        return result

    # 同色等价中心求解会改变棱状态，棱降阶 oracle 对部分状态不完整；
    # 失败时用精确 home 中心重解一遍（精确中心的棱状态始终可降阶）。
    result_exact = _solve_once(work.clone(), cancel_event, progress_callback,
                               prefer_exact_centers=True)
    if result_exact.success:
        return result_exact

    trial = work.clone()
    if _swap_two_center_homes(trial):
        result2 = _solve_once(trial, cancel_event, progress_callback,
                              force_center=True, prefer_exact_centers=True)
        if result2.success:
            return result2
    return result


def _solve_once(cube: Cube5, cancel_event=None, progress_callback=None,
                force_center: bool = False,
                prefer_exact_centers: bool = False) -> SolveResult:
    work = cube.clone()
    all_moves: List[str] = []

    # ---- stage 1: 中心还原（仅当中心颜色未归面时才求解，避免无谓拆棱）----
    center_moves: List[str] = []
    center_msg = ""
    _emit(progress_callback, "centers", 0.05, "stage.centers")
    if centers_are_color_solved(work) and not force_center:
        center_msg = "中心颜色已归面，跳过"
        _emit(progress_callback, "centers", 0.45)
    else:
        def _center_prog(payload):
            done = payload.get("done", 0)
            total = max(1, payload.get("total", 2))
            _emit(progress_callback, "centers", 0.05 + 0.40 * done / total,
                  "stage.centers")

        # 优先同色等价求解（更快）；失败或无收益时回退精确 home 求解。
        cr = (None if prefer_exact_centers
              else solve_centers5_color(work, progress_callback=_center_prog))
        if cr is None or not cr.success:
            cr = solve_centers5(work)
        _emit(progress_callback, "centers", 0.45)
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

    # ---- stage 2: 棱降阶（配翼 + 末段宏级规划；reference ref5 管线）----
    def _reduce_prog(payload):
        vi = payload.get("variant", 0)
        vn = max(1, payload.get("variants", 1))
        _emit(progress_callback, "edge_pairing", 0.45 + 0.45 * vi / vn,
              "stage.edge_pairing")

    emoves, einfo = ref5_reduce.reduce_edges(work, progress_callback=_reduce_prog)
    _emit(progress_callback, "edge_pairing", 0.90, "stage.edge_pairing")
    if emoves is None:
        msg = "棱降阶失败: %s" % einfo.get("note", "未知")
        return SolveResult(
            False, all_moves, msg, 0, len(all_moves),
            [SolveStage("center", center_msg, center_moves),
             SolveStage("reduce_edges", msg, [])],
        )
    ref5_me.apply_macro(work, emoves)
    all_moves.extend(emoves)

    # ---- stage 2b: 中棱朝向修正（消除中棱相对翼的内部翻转）----
    _emit(progress_callback, "orient", 0.92, "stage.orient")
    fix_moves, finfo = ref5_mof.fix_middle_orientation(work)
    if fix_moves is None:
        msg = "中棱朝向修正失败: %s" % finfo.get("error", "未知")
        return SolveResult(
            False, all_moves, msg, 0, len(all_moves),
            [SolveStage("center", center_msg, center_moves),
             SolveStage("reduce_edges", "降阶完成", list(emoves))],
        )
    if fix_moves:
        ref5_me.apply_macro(work, fix_moves)
        all_moves.extend(fix_moves)

    # ---- stage 3: 降阶 3x3 ----
    _emit(progress_callback, "reduced_3x3", 0.95, "stage.reduced_3x3")
    facelets = build_reduced_facelets(work)
    r3 = solve_3x3(facelets)
    if not r3.success:
        return SolveResult(False, all_moves, "降阶 3x3 求解失败: %s" % r3.message,
                           0, len(all_moves),
                           [SolveStage("center", center_msg, center_moves),
                            SolveStage("reduce_edges", "降阶完成", list(emoves)),
                            SolveStage("orient", "朝向修正", list(fix_moves))])

    # ---- stage 4: 回放 3x3 动作到 5x5 ----
    _replay(work, r3.moves)
    all_moves.extend(r3.moves)

    # ---- stage 5: 整段物理层化简（跨阶段抵消），并回放校验 ----
    simplified = simplify_moves(all_moves, cube.n)
    check = cube.clone()
    check.apply_moves(simplified)
    solved = check.is_solved()
    _emit(progress_callback, "reduced_3x3", 1.0, "stage.done")

    return SolveResult(
        solved, simplified,
        "%s，共 %d 步（中心 %d + 棱降阶 %d + 朝向 %d + 3x3 %d，化简前 %d）" % (
            "已还原" if solved else "回放校验未完全还原",
            len(simplified), len(center_moves), len(emoves), len(fix_moves),
            len(r3.moves), len(all_moves)
        ),
        0, len(simplified),
        [SolveStage("center", center_msg, center_moves),
         SolveStage("reduce_edges", "降阶完成", list(emoves)),
         SolveStage("orient", "朝向修正", list(fix_moves)),
         SolveStage("reduce_3x3", "降阶求解", list(r3.moves))],
    )


def solve_5x5_facelets(
    facelets: Dict[str, List[List[str]]],
    cancel_event=None,
    progress_callback=None,
) -> SolveResult:
    """从 facelets 字典求解 5x5（构造 Cube5 后走 solve_5x5）。"""
    from cube.conversion import facelets_to_cubies
    cubies = facelets_to_cubies(facelets, 5)
    cube = Cube5(cubies)
    return solve_5x5(cube, cancel_event=cancel_event, progress_callback=progress_callback)
