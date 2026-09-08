"""生产 5x5 求解器（solver.solver5.solve_5x5）端到端回归。

覆盖移植后的完整流水线：
中心归面 → 棱降阶（ref5 reduce_edges）→ 中棱朝向修正（fix_middle_orientation）
→ 虚拟 3x3（solve_3x3）→ 回放。

关键：`solve_5x5` 返回的 moves 含 M/E/S 物理切片 token，可用
`macro_effect.apply_macro` 回放，也可用 App 的 `decompose_move` + `apply_move`
逐步回放（`Cube5.apply_move` 现已识别 M/E/S）。
"""
import random

import pytest

from cube.cube5 import Cube5
from cube.conversion import cubies_to_facelets, facelets_to_cubies
from renderer.turn import decompose_move
from solver.reduction.ref5.reduce5 import me
from solver.solver5 import solve_5x5, solve_5x5_facelets


def _random_scramble(cube, n, rng):
    faces = ["U", "D", "L", "R", "F", "B"]
    suffixes = ["", "'", "2"]
    wide = ["2U", "2D", "2L", "2R", "2F", "2B"]
    last = None
    for _ in range(n):
        base = rng.choice(wide) if rng.random() < 0.4 else rng.choice(faces)
        mv = base + rng.choice(suffixes)
        if last is not None and mv[0] == last[0]:
            continue
        last = mv
        cube.apply_move(mv)


@pytest.mark.parametrize("seed", [3, 19, 42, 101])
def test_solve_5x5_end_to_end(seed):
    rng = random.Random(seed)
    c = Cube5.solved()
    _random_scramble(c, 40, rng)
    res = solve_5x5(c)
    assert res.success, f"seed {seed} 求解失败: {res.message}"
    assert res.moves, f"seed {seed} 未返回动作"
    check = c.clone()
    me.apply_macro(check, res.moves)
    assert check.is_solved(), f"seed {seed} 回放后未复原: {res.message}"


def test_solve_5x5_already_solved():
    c = Cube5.solved()
    res = solve_5x5(c)
    assert res.success
    check = c.clone()
    if res.moves:
        me.apply_macro(check, res.moves)
    assert check.is_solved()


_APP_POOL = ["U", "D", "F", "B", "R", "L", "u", "d", "f", "b", "r", "l",
             "2U", "2D", "2F", "2B", "2R", "2L"]


def _app_scramble(rng, lo=12, hi=25):
    c = Cube5.solved()
    for _ in range(rng.randint(lo, hi)):
        c.apply_move(rng.choice(_APP_POOL) + rng.choice(["", "'", "2"]))
    return c


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_solve_5x5_from_facelets_roundtrip(seed):
    """App 路径：cubies → facelets → facelets_to_cubies(home==pos) → solve_5x5。

    这类输入的中心 home 不可信，且会触发中棱朝向 GF(2) 奇偶（odd-d）重试。
    """
    rng = random.Random(seed)
    for _ in range(5):
        c = _app_scramble(rng)
        fx = cubies_to_facelets(c.cubies, 5)
        cubies = facelets_to_cubies(fx, 5)
        res = solve_5x5(Cube5(cubies))
        assert res.success, f"seed {seed} 求解失败: {res.message}"
        check = c.clone()
        me.apply_macro(check, res.moves)
        assert check.is_solved(), f"seed {seed} 回放后未复原"


def test_solve_5x5_facelets_api():
    rng = random.Random(11)
    c = _app_scramble(rng)
    fx = cubies_to_facelets(c.cubies, 5)
    res = solve_5x5_facelets(fx)
    assert res.success, f"facelets API 求解失败: {res.message}"
    check = c.clone()
    me.apply_macro(check, res.moves)
    assert check.is_solved()


def _single_turn_string(step):
    """复刻 PlaybackScreen._single_turn_string。"""
    token = step.move_str
    if token and token[0] in ("M", "E", "S"):
        return token[0]
    n_layers = len(step.layers)
    if n_layers > 2:
        return f"{n_layers}{step.base}"
    if n_layers == 2:
        return step.base.lower()
    return step.base


def _app_replay(cube, moves):
    """完全复刻 PlaybackScreen 动画回放：decompose_move + apply_move。"""
    for mv in moves:
        for step in decompose_move(mv, 5):
            for _ in range(step.count):
                cube.apply_move(_single_turn_string(step))


def test_slice_tokens_match_inner_slice():
    """M/E/S 经 apply_move 应与 apply_inner_slice 完全等价。"""
    cases = [("M", "x", 1), ("M'", "x", 3), ("M2", "x", 2),
             ("E", "y", 1), ("E'", "y", 3), ("S", "z", 1), ("S'", "z", 3)]
    for tok, axis, turns in cases:
        a = Cube5.solved()
        a.apply_move(tok)
        b = Cube5.solved()
        b.apply_inner_slice(axis, turns)
        assert a.cubies.keys() == b.cubies.keys()
        for pos in a.cubies:
            ca, cb = a.cubies[pos], b.cubies[pos]
            assert ca.home == cb.home, tok
            assert ca.stickers == cb.stickers, tok


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_solve_5x5_app_playback(seed):
    """App 动画回放路径：M/E/S 与宽层 token 经 decompose_move 逐步回放复原。"""
    rng = random.Random(seed)
    c = _app_scramble(rng)
    fx = cubies_to_facelets(c.cubies, 5)
    res = solve_5x5(Cube5(facelets_to_cubies(fx, 5)))
    assert res.success, f"seed {seed} 求解失败: {res.message}"
    check = c.clone()
    _app_replay(check, res.moves)
    assert check.is_solved(), f"seed {seed} App 回放后未复原"
