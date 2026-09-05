"""5x5 求解器合法动作定义。

标准实体 5x5 的六个面心是固定参考件（定义颜色方向），任何合法移动都不能
置换它们。3/4/5 层宽转会旋转经过中面（法线轴坐标 0），从而把位于中面的
四个固定面心转走，属于非法动作，求解器必须在边界拒绝。

合法动作只包含：
    外层（1 层）：R / L / U / D / F / B
    两层宽转（2 层）：2R / 2L / 2U / 2D / 2F / 2B
    以及各自的 ' 和 2 后缀。

底层引擎仍允许执行 3R/4R 等（保留兼容性与既有动作测试），但求解器边界
不允许生成或接受它们。本模块专门提供「求解器侧」合法性判断。
"""

from typing import List, Sequence

from cube.notation import parse_move_full

# 合法动作：外层 + 两层宽转，每条含 '', "'", "2" 三种后缀。
LEGAL_5X5_CENTER_MOVES: tuple = tuple(
    sorted(
        {
            f"{base}{suffix}"
            for base in ("R", "L", "U", "D", "F", "B",
                         "2R", "2L", "2U", "2D", "2F", "2B")
            for suffix in ("", "'", "2")
        }
    )
)


class IllegalMoveForCube5Solver(ValueError):
    """5x5 求解器试图生成或接受非合法动作时抛出。"""


def is_legal_5x5_solver_move(move: str) -> bool:
    """判断单动作是否为 5x5 求解器可接受的合法动作。"""
    try:
        label, layers, count = parse_move_full(move)
    except ValueError:
        return False
    if label in ("x", "y", "z"):
        return False
    # 合法的层数只有 1（外层）与 2（两层宽转）。
    if layers not in (1, 2):
        return False
    # count 只允许 1/2/3（90/180/270 度）。
    if count not in (1, 2, 3):
        return False
    return True


def assert_legal_5x5_solution_moves(moves: Sequence[str]) -> None:
    """若序列中出现非合法动作则立即抛错。"""
    illegal = [m for m in moves if not is_legal_5x5_solver_move(m)]
    if illegal:
        raise IllegalMoveForCube5Solver(
            "5x5 solver emitted illegal moves: %s" % illegal
        )


def invert_move_string(move: str) -> str:
    """单动作字符串求逆（保持层数前缀）。"""
    label, layers, count = parse_move_full(move)
    inv_count = (4 - count) % 4
    suffix = {1: "", 2: "2", 3: "'"}[inv_count]
    if label in ("x", "y", "z"):
        return label + suffix
    if layers == 1:
        return label + suffix
    return f"{layers}{label}{suffix}"


def invert_moves(moves: Sequence[str]) -> List[str]:
    """动作序列求逆（逆序逐个取逆）。"""
    return [invert_move_string(m) for m in reversed(list(moves))]
