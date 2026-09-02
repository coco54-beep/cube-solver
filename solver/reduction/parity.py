"""4x4 特殊翻棱 (OLL parity) 与交换奇偶 (PLL parity) 检测与处理。

约减完成后，4x4 已等效为 3x3，但仍可能处于 3x3 不可达的状态：
- OLL parity：奇数个"翻棱"（棱组内两翼互换），等价于 3x3 单棱翻转；
- PLL parity：棱组整体置换与角置换奇偶不一致，等价于 3x3 交换两棱。

检测：以 3x3 求解器的返回信息为基准。hkociemba 对不可达状态返回明确
错误（edge flip / corner parity），据此选择修复算法：
- OLL_FIX：r2 B2 U2 l U2 r' U2 r U2 F2 r F2 l' B2 r2
- PLL_FIX：r2 U2 r2 Uw2 r2 u2

说明：我们自己的 validate_3x3 存在对合法状态误报翻棱的缺陷，因此这里
以 hkociemba 求解结果为权威判据，不使用本地翻转计数。
"""

from typing import List, Tuple

from solver.solver3 import solve_3x3
from solver.reduction.reduced_cube import build_reduced_facelets

# 内层切片用 (宽层 + 外层) 组合表示（本项目小写 = 宽层）：
#   内层 r  = r R' , 内层 r2 = r2 R2 ; 内层 l  = l L' , 内层 l2 = l2 L2
#   内层 u2 = u2 U2
OLL_FIX = ["r2 R2", "B2", "U2", "l L'", "U2", "r' R", "U2", "r R'",
           "U2", "F2", "r R'", "F2", "l' L", "B2", "r2 R2"]

PLL_FIX = ["r2 R2", "U2", "r2 R2", "u2", "r2 R2", "u2 U2"]


def detect_parity(cube) -> Tuple[str, str]:
    """检测 4x4 约减后状态是否需要 parity 修复。

    返回 (status, detail)：
        status: "none" | "oll" | "pll"
        detail: 3x3 求解器返回的错误信息（或空串）。
    以 hkociemba 求解返回为权威判据。
    """
    facelets = build_reduced_facelets(cube)
    res = solve_3x3(facelets)
    if res.success:
        return "none", ""
    msg = res.message or ""
    low = msg.lower()
    if "flip" in low or "翻转" in msg:
        return "oll", msg
    if "parity" in low or "奇偶" in msg:
        return "pll", msg
    return "unknown", msg


def apply_parity_fixes(cube, cancel_event=None, progress_callback=None) -> List[str]:
    """检测并修复 parity，返回使用的动作列表（不修改输入 cube）。

    反复检测直到 3x3 求解成功（OLL 修复可能引入 PLL parity，反之亦然）。
    支持 cancel_event（threading.Event）。
    """
    work = cube.clone()
    moves: List[str] = []
    for it in range(6):
        if cancel_event is not None and cancel_event.is_set():
            raise ValueError("parity fixes cancelled")
        if progress_callback is not None:
            progress_callback({"iteration": it, "moves": len(moves)})
        status, detail = detect_parity(work)
        if status == "none":
            return moves
        fix = OLL_FIX if status == "oll" else PLL_FIX
        moves.extend(fix)
        for m in fix:
            for tok in m.split():
                work.apply_move(tok)
    raise ValueError("parity fixes did not converge")
