"""5x5 中心被置换状态的求解回归（3 层转会移动固定面心）。

求解器应先把「当前各面中心」当作目标配色对齐中心，再用原降阶流程，
最终解成六面纯色（固定面心位置可非原位）。本模块不依赖 Kivy，CI 会运行。
"""

import random

from cube.cube5 import Cube5
from cube.conversion import cubies_to_facelets
from cube.scramble import random_scramble, text_to_moves
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


def test_solve_5x5_mixed_slice_scramble_to_solid_faces():
    """3 层转 + 独立切片混合：固定面心被奇置换 → 虚拟 3x3 棱角奇偶不一致。

    回归「中心奇偶翻转」回退（施加一次中层 90° 转再重解）。
    """
    scrambles = [
        "3R U 3F' M E 3U' 3L 3D 3B' S",
        "M E S 3R 3U 3F 3L 3D 3B",
    ]
    for scr in scrambles:
        c = Cube5.solved()
        moves, _ = text_to_moves(scr, n=5)
        c.apply_moves(moves)
        res = solve_5x5(c)
        assert res.success, f"{scr!r} 求解失败: {res.message}"
        check = c.clone()
        me.apply_macro(check, res.moves)
        assert _all_faces_solid(check), f"{scr!r} 回放后未解成六面纯色"
