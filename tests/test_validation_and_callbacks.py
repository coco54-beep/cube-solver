"""validate_3x3 修复与 solve_4x4 取消/进度回调测试。"""

import threading

import pytest

from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.conversion import cubies_to_facelets
from cube.validation import validate_3x3
from solver.solver3 import solve_3x3
from solver.solver4 import solve_4x4
from solver.solver4 import _cube_from_facelets


def _apply(cube, moves):
    for m in moves:
        for tok in m.split():
            cube.apply_move(tok)


class TestValidation3x3Fix:
    """回归：validate_3x3 曾对合法状态误报棱翻转。"""

    @pytest.mark.parametrize("scramble", [
        "R U",
        "R U R' U'",
        "F U",
        "R' F R U'",
        "U2 R2 F' B'",
    ])
    def test_valid_scrambles_pass(self, scramble):
        cube = Cube3.solved()
        for m in scramble.split():
            cube.apply_move(m)
        facelets = cubies_to_facelets(cube.cubies, 3)
        assert validate_3x3(facelets) == []

    def test_single_edge_flip_rejected(self):
        """单棱翻转应被判定非法（翻转和奇数）。"""
        from cube.coordinates import rc_from_pos
        # 合法状态 + 交换 UF 棱的两个 sticker（U[2][1] 与 F[0][1]），颜色计数不变
        cube = Cube3.solved()
        facelets = cubies_to_facelets(cube.cubies, 3)
        ru, cu = rc_from_pos(3, "U", (0, 1, 1))
        rf, cf = rc_from_pos(3, "F", (0, 1, 1))
        facelets["U"][ru][cu], facelets["F"][rf][cf] = (
            facelets["F"][rf][cf], facelets["U"][ru][cu])
        errs = validate_3x3(facelets)
        assert any("翻转" in e for e in errs)

    def test_random_agrees_with_kociemba(self, rng):
        faces = ["R", "L", "U", "D", "F", "B"]
        suff = ["", "'", "2"]
        agree = 0
        for _ in range(40):
            cube = Cube3.solved()
            for _ in range(rng.randint(0, 20)):
                cube.apply_move(rng.choice(faces) + rng.choice(suff))
            facelets = cubies_to_facelets(cube.cubies, 3)
            errs = validate_3x3(facelets)
            res = solve_3x3(facelets)
            assert (not errs) == res.success
            agree += 1
        assert agree == 40


class TestSolve4x4Callbacks:
    def test_cancel_before_solve_fails_fast(self, rng):
        faces = ["R", "L", "U", "D", "F", "B"]
        suff = ["", "'", "2"]
        cube = Cube4.solved()
        for _ in range(12):
            cube.apply_move(rng.choice(faces).lower() + rng.choice(suff))
        ev = threading.Event()
        ev.set()
        result = solve_4x4(cube, cancel_event=ev)
        assert not result.success
        assert "cancelled" in result.message.lower()

    def test_cancel_not_set_solves(self, rng):
        faces = ["R", "L", "U", "D", "F", "B"]
        suff = ["", "'", "2"]
        cube = Cube4.solved()
        for _ in range(12):
            cube.apply_move(rng.choice(faces).lower() + rng.choice(suff))
        ev = threading.Event()
        result = solve_4x4(cube, cancel_event=ev)
        assert result.success

    def test_progress_callback_fired(self, rng):
        faces = ["R", "L", "U", "D", "F", "B"]
        suff = ["", "'", "2"]
        cube = Cube4.solved()
        for _ in range(12):
            cube.apply_move(rng.choice(faces).lower() + rng.choice(suff))
        events = []
        result = solve_4x4(cube, progress_callback=events.append)
        assert result.success
        # 中心 / 棱配对 / parity / 3x3 四个阶段至少都上报过 stage 事件
        stage_events = [e for e in events if "stage" in e]
        names = {e["stage"] for e in stage_events}
        assert {"centers", "edge_pairing", "reduced_3x3"} <= names

    def test_facelet_entry_cancel(self, rng):
        from solver.solver4 import solve_4x4_facelets
        faces = ["R", "L", "U", "D", "F", "B"]
        suff = ["", "'", "2"]
        cube = Cube4.solved()
        for _ in range(12):
            cube.apply_move(rng.choice(faces).lower() + rng.choice(suff))
        facelets = cubies_to_facelets(cube.cubies, 4)
        ev = threading.Event()
        ev.set()
        result = solve_4x4_facelets(facelets, cancel_event=ev)
        assert not result.success
