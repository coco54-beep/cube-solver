"""求解器包：2x2、3x3、4x4 与 5x5 还原。"""

from solver.solver3 import solve_3x3  # noqa: F401
from solver.solver4 import solve_4x4, solve_4x4_facelets  # noqa: F401
from solver.solver2 import solve_2x2, solve_2x2_facelets  # noqa: F401
from solver.reduction import (  # noqa: F401
    CenterSolveError,
    CenterSolver4,
    solve_centers,
)

# solver5 只需在真正求解 5x5 时才加载：它会触发 ref5 宏库构建（首次约 7s，
# 手机更慢），若在此处急切 import，导入任意 solver.solverN 都会连带在冷启动
# 做这份重活，极易在低端机首启被 oom/ANR 杀掉。改为惰性（PEP 562）。
def __getattr__(name):
    if name in ("solve_5x5", "solve_5x5_facelets"):
        from solver.solver5 import solve_5x5, solve_5x5_facelets
        return {"solve_5x5": solve_5x5, "solve_5x5_facelets": solve_5x5_facelets}[name]
    raise AttributeError("module 'solver' has no attribute %r" % name)
