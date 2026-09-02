"""4x4 棱块配对 / 降阶 / parity / 完整求解测试。

依赖：
- 中心还原使用 solve_centers（joint_dist.bin 预计算表）。
- 3x3 求解使用 hkociemba twophase（已随包提供预生成表）。
- 完整求解验证：随机打乱 -> solve_4x4 -> 应用全部动作 -> is_solved()。
"""

import random

import pytest

from cube.cube4 import Cube4
from solver.reduction.edge_pairing import edges_paired, matched_slots, pair_edges
from solver.reduction.reduced_cube import build_reduced_facelets
from solver.reduction.parity import apply_parity_fixes, detect_parity
from solver.reduction.center_solver import solve_centers
from solver.solver4 import solve_4x4, solve_4x4_facelets
from solver.solver3 import solve_3x3
from cube.conversion import cubies_to_facelets


def _sig(cube):
    return tuple(sorted(
        (tuple(p), tuple(c.home), tuple(sorted(c.stickers.items())))
        for p, c in cube.cubies.items()
    ))


def _apply(cube, moves):
    for m in moves:
        for tok in m.split():
            cube.apply_move(tok)


def _center_solved_cube(rng, scramble_len=12):
    faces = ["R", "L", "U", "D", "F", "B"]
    suff = ["", "'", "2"]
    cube = Cube4.solved()
    moves = [rng.choice(faces).lower() + rng.choice(suff)
             for _ in range(scramble_len)]
    cube.apply_moves(moves)
    center_moves = solve_centers(cube)
    cube.apply_moves(center_moves)
    return cube, moves


@pytest.fixture(scope="module")
def rng():
    return random.Random(20250829)


class TestPairing:
    def test_solved_edges_paired(self):
        assert edges_paired(Cube4.solved())

    def test_pairing_from_scramble(self, rng):
        for _ in range(5):
            cube, sc = _center_solved_cube(rng)
            before = _sig(cube)
            moves = pair_edges(cube)
            assert _sig(cube) == before  # 不修改输入
            work = Cube4.solved()
            work.apply_moves(sc)
            work.apply_moves(solve_centers(work))
            _apply(work, moves)
            assert edges_paired(work)

    def test_pairing_preserves_centers(self, rng):
        from solver.reduction.center_solver import centers_solved
        cube, sc = _center_solved_cube(rng)
        moves = pair_edges(cube)
        work = Cube4.solved()
        work.apply_moves(sc)
        work.apply_moves(solve_centers(work))
        _apply(work, moves)
        assert centers_solved(work)

    def test_matched_slots_full(self, rng):
        cube, sc = _center_solved_cube(rng)
        moves = pair_edges(cube)
        work = Cube4.solved()
        work.apply_moves(sc)
        work.apply_moves(solve_centers(work))
        _apply(work, moves)
        assert matched_slots(work) == 12


class TestReducedCube:
    def test_solved_maps_to_solved_3x3(self):
        cube = Cube4.solved()
        reduced = build_reduced_facelets(cube)
        res = solve_3x3(reduced)
        assert res.success and res.move_count == 0

    def test_reduced_3x3_solvable_after_full(self, rng):
        for _ in range(5):
            cube, sc = _center_solved_cube(rng, 15)
            moves = pair_edges(cube)
            work = Cube4.solved()
            work.apply_moves(sc)
            work.apply_moves(solve_centers(work))
            _apply(work, moves)
            pm = apply_parity_fixes(work)
            _apply(work, pm)
            reduced = build_reduced_facelets(work)
            res = solve_3x3(reduced)
            assert res.success, res.message


class TestParity:
    def test_solved_no_parity(self):
        cube = Cube4.solved()
        status, _ = detect_parity(cube)
        assert status == "none"

    def test_oll_parity_detected(self):
        cube = Cube4.solved()
        from solver.reduction.parity import OLL_FIX
        for m in OLL_FIX:
            for tok in m.split():
                cube.apply_move(tok)
        status, _ = detect_parity(cube)
        assert status == "oll"
    def test_pll_parity_detected(self):
        cube = Cube4.solved()
        from solver.reduction.parity import PLL_FIX
        for m in PLL_FIX:
            for tok in m.split():
                cube.apply_move(tok)
        status, _ = detect_parity(cube)
        assert status == "pll"

    def test_parity_fix_restores_solvable(self):
        cube = Cube4.solved()
        from solver.reduction.parity import OLL_FIX, PLL_FIX
        for m in OLL_FIX + PLL_FIX:
            for tok in m.split():
                cube.apply_move(tok)
        moves = apply_parity_fixes(cube)
        assert moves
        work = cube.clone()
        for m in moves:
            for tok in m.split():
                work.apply_move(tok)
        status, _ = detect_parity(work)
        assert status == "none"


class TestFullSolve:
    def test_solve_random_scrambles(self, rng):
        faces = ["R", "L", "U", "D", "F", "B"]
        suff = ["", "'", "2"]
        for i in range(6):
            scramble = [rng.choice(faces).lower() + rng.choice(suff)
                        for _ in range(25)]
            cube = Cube4.solved()
            cube.apply_moves(scramble)
            result = solve_4x4(cube)
            assert result.success, result.message
            verify = Cube4.solved()
            verify.apply_moves(scramble)
            _apply(verify, result.moves)
            assert verify.is_solved(), f"case {i} not solved"

    def test_solve_solved_cube(self):
        result = solve_4x4(Cube4.solved())
        assert result.success
        assert result.move_count == 0

    def test_result_stages(self, rng):
        faces = ["R", "L", "U", "D", "F", "B"]
        suff = ["", "'", "2"]
        cube = Cube4.solved()
        cube.apply_moves([rng.choice(faces).lower() + rng.choice(suff)
                          for _ in range(12)])
        result = solve_4x4(cube)
        assert result.success
        names = [s.name for s in result.stages]
        assert names[:2] == ["centers", "edge_pairing"]
        assert "reduced_3x3" in names

    def test_facelet_entry(self, rng):
        from solver.solver4 import _cube_from_facelets
        faces = ["R", "L", "U", "D", "F", "B"]
        suff = ["", "'", "2"]
        cube = Cube4.solved()
        cube.apply_moves([rng.choice(faces).lower() + rng.choice(suff)
                          for _ in range(15)])
        facelets = cubies_to_facelets(cube.cubies, 4)
        result = solve_4x4_facelets(facelets)
        assert result.success, result.message
        # 从 facelets 重建的立方体与原始打乱状态颜色一致
        rebuilt = _cube_from_facelets(facelets)
        assert cubies_to_facelets(rebuilt.cubies, 4) == facelets
