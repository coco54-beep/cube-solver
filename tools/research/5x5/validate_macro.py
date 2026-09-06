"""验证实验A找到的 free-slice 宏：在真实 Cube5 上重放，确认
合法性、中心最终按颜色归面、以及对目标棱/翼的作用。"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cube.cube5 import Cube5
from solver.edge5.state import center_color_off, centers_are_color_solved, \
    is_edge_paired, is_edge_solved, paired_count
from solver.edge5.compact_state import state_of
from solver.edge5.free_slice import edge_relation, target_pieces

MACROS = [
    ("2L", "D", "R'", "D'", "2L'"),
    ("2L'", "U", "R", "U'", "2L"),
    ("2L2", "B", "R2", "B'", "2L2"),
    ("2U", "F'", "U'", "F", "2U'"),
    ("2U'", "F'", "U", "F", "2U"),
    ("2U2", "F'", "U2", "F", "2U2"),
]


def main():
    for m in MACROS:
        for mv in m:
            from solver.center5.legal_moves import is_legal_5x5_solver_move
            assert is_legal_5x5_solver_move(mv), f"illegal {mv}"
        c = Cube5.solved()
        c.apply_moves(m)
        co = center_color_off(c)
        pc = paired_count(c)
        print(f"  {' '.join(m):22s}  center_color_off={co}  paired_count={pc}/12")


if __name__ == "__main__":
    main()
