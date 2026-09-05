"""2x2 求解器与校验测试。"""

import random

from cube.cube2 import Cube2
from cube.conversion import cubies_to_facelets, facelets_to_cubies
from cube.facelet_model import FaceletCube
from cube.validation import validate_2x2
from solver.solver2 import _2x2State, solve_2x2, solve_2x2_facelets, _FACES


def test_2x2_solved_state_roundtrip():
    """状态机制：extract / apply / solved_state 与真实 Cube2 一致且逆操作可还原。"""
    eng = _2x2State()
    solve = Cube2.solved()
    # 单个 90° 转动：apply 后状态与真实 cube 一致
    for face in _FACES:
        st = eng.solved_state()
        nxt = eng.apply(st, face, 1)
        cube = Cube2.solved()
        cube.apply_move(face)
        assert eng.extract(cube) == nxt
    # 逆向可还原
    st = eng.solved_state()
    nxt = eng.apply(st, "R", 1)
    back = eng.apply(nxt, "R", 3)
    assert back == st


def test_2x2_solve_short_scramble():
    """随机短打乱 -> 求解 -> 应用到 Cube2 后还原。"""
    rng = random.Random(1)
    for _ in range(6):
        scramble = [
            rng.choice(_FACES) + rng.choice(["", "'", "2"]) for _ in range(7)
        ]
        cube = Cube2.solved()
        for m in scramble:
            cube.apply_move(m)
        res = solve_2x2(cube, time_limit=10.0)
        assert res.success
        assert 0 <= res.move_count <= 7
        v = Cube2.solved()
        for m in scramble:
            v.apply_move(m)
        for m in res.moves:
            v.apply_move(m)
        assert v.is_solved()


def test_2x2_validate_reachable_and_illegal():
    """校验：随机打乱合法；非法颜色计数被判非法。"""
    rng = random.Random(2)
    for _ in range(6):
        cube = Cube2.solved()
        for m in [rng.choice(_FACES) + rng.choice(["", "'", "2"]) for _ in range(6)]:
            cube.apply_move(m)
        fc = FaceletCube(cubies_to_facelets(cube.cubies, 2), 2)
        assert fc.validate() == []
    # 非法：颜色计数失衡
    cube = Cube2.solved()
    fac = cubies_to_facelets(cube.cubies, 2)
    fac["U"][0][0] = "R"
    assert validate_2x2(fac) != []


def test_2x2_solve_facelets_input_path():
    """从 facelets（home=pos 的 cubies，即真实录入路径）求解可还原。"""
    rng = random.Random(3)
    for _ in range(6):
        scramble = [
            rng.choice(_FACES) + rng.choice(["", "'", "2"]) for _ in range(6)
        ]
        cube = Cube2.solved()
        for m in scramble:
            cube.apply_move(m)
        fac = cubies_to_facelets(cube.cubies, 2)
        res = solve_2x2_facelets(fac, time_limit=10.0)
        assert res.success
        v = Cube2(facelets_to_cubies(fac, 2))
        for m in res.moves:
            v.apply_move(m)
        assert v.is_solved()
