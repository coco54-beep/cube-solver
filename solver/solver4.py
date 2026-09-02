"""4x4 完整求解器（降阶法）。

流程：
1. 中心还原（solve_centers）
2. 棱块配对（pair_edges）
3. Parity 检测与修复（apply_parity_fixes）
4. 降阶为 3x3 并调用 3x3 求解器（solve_3x3）

对外入口：solve_4x4(cube) / solve_4x4_facelets(facelets)，返回 SolveResult。
"""

import time
from typing import Dict, List

from cube.cube4 import Cube4
from cube.conversion import facelets_to_cubies
from cube.notation import parse_move_str, suffix_for_count
from solver.result import SolveResult, SolveStage
from solver.reduction.center_solver import solve_centers, solve_centers_variant
from solver.reduction.edge_pairing import pair_edges, edges_paired
from solver.reduction.parity import apply_parity_fixes
from solver.reduction.reduced_cube import build_reduced_facelets
from solver.solver3 import solve_3x3


def _compress_moves(moves: List[str]) -> List[str]:
    """压缩动作序列：合并相邻的同面同宽层动作（如 R R -> R2，R R' -> 空）。

    只做安全等价变换，不改变序列效果。
    """
    stacked = []  # ((label, is_wide), count)
    for m in moves:
        for tok in m.split():
            label, is_wide, count = parse_move_str(tok)
            key = (label, is_wide)
            while stacked and stacked[-1][0] == key:
                prev_count = stacked[-1][1]
                count = (prev_count + count) % 4
                stacked.pop()
            if count != 0:
                stacked.append((key, count))
    out = []
    for (label, is_wide), count in stacked:
        base = label.lower() if is_wide else label
        out.append(base + suffix_for_count(count))
    return out


def _apply_moves(cube, moves) -> None:
    """应用动作列表；兼容形如 "r2 R2"（内层切片组合）的多记号项。"""
    for m in moves:
        for tok in m.split():
            cube.apply_move(tok)


def _expand_moves(moves):
    """把可能含多记号的动作列表展开为单记号列表。

    例如 "r2 R2"（内层切片组合）会被拆成 "r2"、"R2"，
    使下游（播放动画、apply_moves）能逐条解析执行。
    """
    flat = []
    for m in moves:
        flat.extend(m.split())
    return flat


# 择优时额外尝试的等价最优中心解数量（不含默认解）。
# 默认 4 -> 共 5 条中心解参与择优。
_CENTER_SELECT_EXTRA = 4

# 尾段配棱 beam 参数（贪心只在最后几根易局部最优，仅对最终赢家启用一次）。
_PAIR_TAIL_WIDTH = 8
_PAIR_TAIL_NODES = 500
_PAIR_TAIL_MATCHED = 7

# 只有候选解显著优于默认解（压缩步数差 >= 该值）才切换。
_SELECT_MARGIN = 2


def _select_reduction(cube, cancel_event=None):
    """在若干条等价最优中心解中，选「中心 + 配棱 + parity」最短的一条，并缓存结果。

    决策完全基于确定性量（中心解 + 贪心配棱 + parity 修复，三者都可由固定算法
    复现），不受 3x3 求解抖动影响；只有显著更优（>= _SELECT_MARGIN）才切换，
    因此「中心+配棱+parity」这一段绝不劣于默认流水线。随后对赢家做一次配棱尾段
    beam 精搜（同样只在确定性 reduction 更短时接受），最后才跑一次 reduced 3x3。

    返回 (center_moves, edge_moves, parity_moves_flat, solve3_moves)。
    """
    def _reduce(center_moves, tail=False):
        c2 = cube.clone()
        c2.apply_moves(center_moves)
        edge_moves = pair_edges(
            c2, cancel_event=cancel_event,
            tail_width=(_PAIR_TAIL_WIDTH if tail else 0),
            tail_max_nodes=_PAIR_TAIL_NODES,
            tail_matched=_PAIR_TAIL_MATCHED,
        )
        c3 = c2.clone()
        c3.apply_moves(edge_moves)
        parity_moves = apply_parity_fixes(c3, cancel_event=cancel_event)
        parity_flat = _expand_moves(parity_moves)
        c3.apply_moves(parity_flat)
        red_score = len(_compress_moves(
            list(center_moves) + list(edge_moves) + parity_flat
        ))
        return (red_score, center_moves, edge_moves, parity_flat, c3)

    center0 = solve_centers(cube, cancel_event=cancel_event)
    det = _reduce(center0)
    best = det
    for seed in range(1, _CENTER_SELECT_EXTRA + 1):
        cv = solve_centers_variant(cube, seed, cancel_event=cancel_event)
        cand = _reduce(cv)
        if cand[0] < best[0]:
            best = cand
    if not (best[0] < det[0] - _SELECT_MARGIN):
        best = det
    # 竞争池：贪心默认解必在其中，故结果绝不低于默认流水线。
    pool = [det, best]
    if _PAIR_TAIL_WIDTH > 0:
        # 尾段 beam 只对默认解与贪心最优解各重配对一次，结果加入竞争池；
        # 即使某条 beam 结果更差，贪心版本仍在池内兜底。
        pool.append(_reduce(det[1], tail=True))
        if best is not det:
            pool.append(_reduce(best[1], tail=True))
    chosen = min(pool, key=lambda r: r[0])
    # 最后才跑一次 reduced 3x3（minimize=True：目标递减试探，输出更短且更稳定）。
    res = solve_3x3(build_reduced_facelets(chosen[4]), minimize=True)
    if not res.success:
        raise ValueError("3x3 阶段失败")
    solve3_moves = list(res.moves)
    return chosen[1], chosen[2], chosen[3], solve3_moves


def solve_4x4(cube, cancel_event=None, progress_callback=None) -> SolveResult:
    """求解一个 4x4 魔方（Cube4 实例），返回带分阶段的 SolveResult。

    支持 cancel_event（threading.Event，设置后中止求解并返回失败结果）与
    progress_callback（每个阶段完成时回调 dict，含 stage / moves 等）。
    """
    t0 = time.perf_counter()
    work = cube.clone()
    stages: List[SolveStage] = []
    all_moves: List[str] = []

    def _report(stage_name: str, stage_moves: List[str]) -> None:
        if progress_callback is None:
            return
        progress_callback({
            "stage": stage_name,
            "moves": len(stage_moves),
            "total_moves": len(all_moves),
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        })

    # 1+2+3. 中心还原 + 棱块配对 + parity + reduced 3x3：在若干条等价最优
    # 中心解中按「完整解」择优。_select_reduction 返回已按完整长度选好的
    # 中心/配棱/parity/3x3 动作，默认解必在候选中，故不劣于原流水线。
    try:
        center_moves, edge_moves, parity_flat, solve3_moves = _select_reduction(
            cube, cancel_event=cancel_event
        )
    except Exception as exc:
        return SolveResult(False, [], str(exc),
                           int((time.perf_counter() - t0) * 1000), 0, stages)
    _apply_moves(work, center_moves)
    all_moves.extend(center_moves)
    stages.append(SolveStage("centers", "中心还原", center_moves))
    _report("centers", center_moves)

    _apply_moves(work, edge_moves)
    all_moves.extend(edge_moves)
    stages.append(SolveStage("edge_pairing", "棱块配对", edge_moves))
    _report("edge_pairing", edge_moves)
    if not edges_paired(work):
        return SolveResult(False, all_moves, "棱块配对失败",
                           int((time.perf_counter() - t0) * 1000),
                           len(all_moves), stages)

    _apply_moves(work, parity_flat)
    all_moves.extend(parity_flat)
    stages.append(SolveStage("parity", "OLL/PLL 特殊处理", parity_flat))
    _report("parity", parity_flat)

    _apply_moves(work, solve3_moves)
    all_moves.extend(solve3_moves)
    stages.append(SolveStage("reduced_3x3", "按3阶方式还原", solve3_moves))
    _report("reduced_3x3", solve3_moves)

    # 校验
    ok = work.is_solved()
    elapsed = int((time.perf_counter() - t0) * 1000)
    message = "solved" if ok else "求解结果未通过最终校验"
    # 压缩相邻同面动作，缩短总步数（安全等价变换）。
    all_moves = _compress_moves(all_moves)
    return SolveResult(ok, all_moves, message, elapsed, len(all_moves), stages)


def _rebuild_center_homes(cubies, color_to_face=None) -> None:
    """修正中心块 home 面。

    facelets_to_cubies 生成 cubie 时 home=pos，但中心还原求解器按 home 的
    面判定中心归属。中心块只有一个 sticker，按「颜色→面」映射反查该颜色
    所属面，并把 home 设在该面的任一标准槽位（求解器只使用 home 的面）。

    color_to_face: 若给定（dict 颜色->面字母），用该动态映射（支持中心色
    整体换面/随机配色）；否则回退到 DEFAULT_COLORS 标准配色。
    """
    from cube.colors import DEFAULT_COLORS
    from primitives import CENTER_HOMES
    if color_to_face is None:
        color_to_face = {c: f for f, c in DEFAULT_COLORS.items()}
    for cub in cubies.values():
        if len(cub.stickers) != 1:
            continue
        (color,) = cub.stickers.values()
        face = color_to_face[color]
        cub.home = CENTER_HOMES[face][0]


def _face_color_map(facelets) -> dict:
    """从 facelets 推导「颜色->面」映射，支持中心色整体换面。

    仅当某面中心 2x2 四格颜色一致（中心未被宽层打乱）时，才以该颜色作为
    该面基准色；否则跳过。最后用 DEFAULT_COLORS 补齐未推导的颜色，
    因此宽层打乱（中心分散）会自动回退到标准配色。
    """
    from cube.colors import DEFAULT_COLORS
    mapping = {}
    for f, grid in facelets.items():
        m = len(grid) // 2
        cells = {grid[m - 1][m - 1], grid[m - 1][m], grid[m][m - 1], grid[m][m]}
        if len(cells) == 1:
            mapping[cells.pop()] = f
    # 用 DEFAULT_COLORS（面->颜色）补齐未推导的颜色，回退标准配色
    for f, c in DEFAULT_COLORS.items():
        mapping.setdefault(c, f)
    return mapping


def _cube_from_facelets(facelets) -> Cube4:
    """从 facelets 构造 Cube4，并按录入中心色（可整体换面）修正 home 面。"""
    cubies = facelets_to_cubies(facelets, 4)
    _rebuild_center_homes(cubies, _face_color_map(facelets))
    return Cube4(cubies)


def solve_4x4_facelets(
    facelets: Dict[str, List[List[str]]],
    cancel_event=None,
    progress_callback=None,
) -> SolveResult:
    """从 facelets 字典求解 4x4（用户录入接口）。

    支持 cancel_event 与 progress_callback（透传给 solve_4x4）。
    """
    cube = _cube_from_facelets(facelets)
    return solve_4x4(
        cube,
        cancel_event=cancel_event,
        progress_callback=progress_callback,
    )
