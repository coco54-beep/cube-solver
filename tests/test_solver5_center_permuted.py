"""5x5 中心被置换状态的求解回归（3 层转会移动固定面心）。

求解器应先把「当前各面中心」当作目标配色对齐中心，再用原降阶流程，
最终解成六面纯色（固定面心位置可非原位）。本模块不依赖 Kivy，CI 会运行。
"""

import random

from cube.cube5 import Cube5
from cube.conversion import cubies_to_facelets
from cube.scramble import random_scramble
from solver.reduction.ref5.reduce5 import me
from solver.solver5 import solve_5x5


def _all_faces_solid(cube) -> bool:
    fx = cubies_to_facelets(cube.cubies, 5)
    return all(len({c for row in g for c in row}) == 1 for g in fx.values())


def _centers_moved(cube) -> bool:
    fx = cubies_to_facelets(cube.cubies, 5)
    sol = cubies_to_facelets(Cube5.solved().cubies, 5)
    return any(fx[f][2][2] != sol[f][2][2] for f in fx)


def test_random_scramble_moves_fixed_centers():
    c = Cube5.solved()
    c.apply_moves(random_scramble(5, rng=random.Random(0)))
    assert _centers_moved(c)


def test_solve_5x5_with_moved_centers_to_solid_faces():
    for seed in (0, 5):
        c = Cube5.solved()
        c.apply_moves(random_scramble(5, rng=random.Random(seed)))
        res = solve_5x5(c)
        assert res.success, f"seed {seed} 求解失败: {res.message}"
        check = c.clone()
        me.apply_macro(check, res.moves)
        assert _all_faces_solid(check), f"seed {seed} 回放后未解成六面纯色"
