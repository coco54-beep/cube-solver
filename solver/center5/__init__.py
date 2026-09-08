"""5x5 中心求解相关：合法动作、中心轨道、活动中心 3-cycle 基元。"""

from .legal_moves import (
    LEGAL_5X5_CENTER_MOVES,
    IllegalMoveForCube5Solver,
    assert_legal_5x5_solution_moves,
    invert_move_string,
    invert_moves,
    is_legal_5x5_solver_move,
)
from .orbits import (
    CenterOrbitKind,
    center_positions,
    compute_center_orbits,
    kind_of_position,
    orbit_kinds,
)
from .primitives import (
    CORNER_BACKUP,
    CORNER_MAIN,
    EDGE_BACKUP,
    EDGE_MAIN,
    CENTER_PRIMITIVES,
    CENTER_ORDER,
    CenterPrimitive,
    PrimitiveAnalysis,
    analyze_cube5_replay,
    analyze_center_permutation,
    check_primitive_inverse,
    check_primitive_triple_restores_centers,
    validate_center_primitive,
)
from .conjugation import (
    find_setup,
    conjugate_cycle,
)
from .solver import (
    CenterSolveResult,
    solve_centers5,
)
from .color_solver import (
    solve_centers5_color,
)

__all__ = [
    "LEGAL_5X5_CENTER_MOVES",
    "IllegalMoveForCube5Solver",
    "assert_legal_5x5_solution_moves",
    "invert_move_string",
    "invert_moves",
    "is_legal_5x5_solver_move",
    "CenterOrbitKind",
    "center_positions",
    "compute_center_orbits",
    "kind_of_position",
    "orbit_kinds",
    "CORNER_BACKUP",
    "CORNER_MAIN",
    "EDGE_BACKUP",
    "EDGE_MAIN",
    "CENTER_PRIMITIVES",
    "CENTER_ORDER",
    "CenterPrimitive",
    "PrimitiveAnalysis",
    "analyze_cube5_replay",
    "analyze_center_permutation",
    "check_primitive_inverse",
    "check_primitive_triple_restores_centers",
    "validate_center_primitive",
    "find_setup",
    "conjugate_cycle",
    "CenterSolveResult",
    "solve_centers5",
    "solve_centers5_color",
]
