"""求解器包：3x3 与 4x4 还原。"""

from solver.solver3 import solve_3x3  # noqa: F401
from solver.solver4 import solve_4x4, solve_4x4_facelets  # noqa: F401
from solver.reduction import (  # noqa: F401
    CenterSolveError,
    CenterSolver4,
    solve_centers,
)
