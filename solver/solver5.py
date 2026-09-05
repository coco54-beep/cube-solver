"""5x5 求解器。

当前状态：5x5 降阶求解器（中心还原 + 三块棱配对 + 降阶 3x3）尚未实现。

5x5 的中心与棱块编排与 4x4 差异很大：
- 每面有 9 个中心块（含 1 个真中心），共 54 块；
- 每个棱槽有 3 块棱（而非 4x4 的 2 块翼）；
- 不存在「纯中心」的换位式子（任何移动中心的动作都会附带扰动棱/角块），
  因此中心还原需要允许扰动棱/角（之后在配对/降阶阶段再统一处理），
  无法直接复用 4x4 基于预计算表（joint_dist.bin / p4_table.bin）的中心求解器。

本模块提供 solve_5x5 / solve_5x5_facelets 入口，当前均返回明确的
「尚未实现」失败结果，供上层 UI/服务层安全接收，避免崩溃。
"""

from typing import Dict, List

from cube.cube5 import Cube5
from solver.result import SolveResult, SolveStage


def solve_5x5(cube: Cube5, cancel_event=None, progress_callback=None) -> SolveResult:
    """求解 5x5。当前未实现，返回明确的失败结果。"""
    return SolveResult(
        False,
        [],
        "5x5 求解尚未实现",
        0,
        0,
        [SolveStage("not_implemented", "5x5 求解尚未实现")],
    )


def solve_5x5_facelets(
    facelets: Dict[str, List[List[str]]],
    cancel_event=None,
    progress_callback=None,
) -> SolveResult:
    """从 facelets 字典求解 5x5。当前未实现，返回明确的失败结果。"""
    return solve_5x5(None, cancel_event=cancel_event, progress_callback=progress_callback)
