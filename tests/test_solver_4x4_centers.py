"""4x4 中心还原求解器测试（两阶段分解：联合 U+D -> 侧面）。

Phase A 距离表在模块内用深度受限 BFS (depth<=6) 构建，
覆盖本文件全部测试用例的联合距离 (<=6)。
Phase B 查预生成的 p4_table.bin（完整轨道, max distance 14）。
"""

import random
import struct
import threading

import pytest

from cube.cube4 import Cube4
from solver.reduction.center_solver import (
    GOAL,
    IDENT_CODE,
    JOINT_MOVE_LABELS,
    CenterSolveError,
    CenterSolver4,
    build_joint_bfs,
    centers_solved,
    combined_to_rank,
    extract_joint,
    extract_side_code,
    solve_centers,
)

UD_MOVES = ["u", "u'", "d", "d'"]
SIDE_ONLY_MOVES = ["F", "F'", "B", "B'", "R", "R'", "L", "L'"]
JOINT_AFFECTING_MOVES = [
    "F", "F'", "B", "B'", "R", "R'", "L", "L'",
    "f", "f'", "b", "b'", "r", "r'", "l", "l'",
    "u", "u'", "d", "d'",
]


def _sig(cube: Cube4):
    """完整状态签名：全部 cubie 的位置 + home + sticker。"""
    return tuple(sorted(
        (tuple(p), tuple(c.home), tuple(sorted(c.stickers.items())))
        for p, c in cube.cubies.items()
    ))


@pytest.fixture(scope="module")
def dist6():
    dist, stats = build_joint_bfs(max_depth=6)
    assert stats["max_depth_reached"] == 6
    return dist


@pytest.fixture(scope="module")
def solver(dist6):
    s = CenterSolver4(joint_dist=dist6)
    yield s
    s.close()


class TestSanity:
    def test_joint_move_labels(self):
        assert len(JOINT_MOVE_LABELS) == 10
        for lab in JOINT_MOVE_LABELS:
            assert lab in ("F", "B", "R", "L", "f", "b", "r", "l", "u", "d")


class TestBasics:
    def test_solved_returns_empty(self, solver):
        cube = Cube4.solved()
        assert solver.solve(cube) == []

    def test_extract_solved(self):
        cube = Cube4.solved()
        assert extract_joint(cube) == GOAL
        assert extract_side_code(cube) == IDENT_CODE
        assert centers_solved(cube)

    def test_input_not_mutated(self, solver):
        cube = Cube4.solved()
        cube.apply_moves(["f", "u", "r", "b", "u'", "f'"])
        before = _sig(cube)
        solver.solve(cube)
        assert _sig(cube) == before


class TestSingleMoves:
    @pytest.mark.parametrize("label", JOINT_MOVE_LABELS)
    def test_single_wide_move_solves(self, solver, label):
        cube = Cube4.solved()
        cube.apply_move(label)
        moves = solver.solve(cube)
        assert isinstance(moves, list)
        fresh = Cube4.solved()
        fresh.apply_moves([label] + moves)
        assert centers_solved(fresh)

    @pytest.mark.parametrize("label", UD_MOVES)
    def test_ud_slice_solves(self, solver, label):
        cube = Cube4.solved()
        cube.apply_move(label)
        assert extract_joint(cube) == GOAL
        assert extract_side_code(cube) != IDENT_CODE
        moves = solver.solve(cube)
        assert len(moves) > 0
        fresh = Cube4.solved()
        fresh.apply_moves([label] + moves)
        assert centers_solved(fresh)

    @pytest.mark.parametrize("label", SIDE_ONLY_MOVES)
    def test_single_side_move_solves(self, solver, label):
        cube = Cube4.solved()
        cube.apply_move(label)
        assert extract_joint(cube) == GOAL
        moves = solver.solve(cube)
        fresh = Cube4.solved()
        fresh.apply_moves([label] + moves)
        assert centers_solved(fresh)

    SINGLE_LAYER_UD = ["U", "U'", "D", "D'"]

    @pytest.mark.parametrize("label", SINGLE_LAYER_UD)
    def test_single_layer_ud_noop(self, solver, label):
        cube = Cube4.solved()
        cube.apply_move(label)
        assert extract_joint(cube) == GOAL
        assert extract_side_code(cube) == IDENT_CODE
        assert solver.solve(cube) == []


class TestRandom:
    def test_random_cases(self, solver):
        rng = random.Random(20240827)
        for i in range(20):
            walk = [JOINT_MOVE_LABELS[rng.randrange(len(JOINT_MOVE_LABELS))]
                    for _ in range(rng.randint(0, 6))]
            cube = Cube4.solved()
            cube.apply_moves(walk)
            before = _sig(cube)
            moves = solver.solve(cube)
            assert _sig(cube) == before, f"input mutated at case {i}"
            fresh = Cube4.solved()
            fresh.apply_moves(walk + moves)
            assert centers_solved(fresh), f"case {i} walk={walk} moves={moves}"

    def test_deterministic(self, solver):
        rng = random.Random(7)
        walk = [JOINT_MOVE_LABELS[rng.randrange(len(JOINT_MOVE_LABELS))]
                for _ in range(6)]
        cube = Cube4.solved()
        cube.apply_moves(walk)
        assert solver.solve(cube) == solver.solve(cube)

    def test_mixed_scramble(self, solver):
        rng = random.Random(99173)
        for i in range(30):
            walk = [JOINT_AFFECTING_MOVES[rng.randrange(len(JOINT_AFFECTING_MOVES))]
                    for _ in range(rng.randint(1, 6))]
            cube = Cube4.solved()
            cube.apply_moves(walk)
            before = _sig(cube)
            moves = solver.solve(cube)
            assert _sig(cube) == before, f"input mutated at case {i}"
            fresh = Cube4.solved()
            fresh.apply_moves(walk + moves)
            assert centers_solved(fresh), f"case {i} walk={walk} moves={moves}"


class TestErrors:
    def test_missing_table_raises(self, dist6):
        s = CenterSolver4(joint_dist=dist6, table_path="nonexistent_table.bin")
        cube = Cube4.solved()
        cube.apply_move("u")
        with pytest.raises(CenterSolveError):
            s.solve(cube)

    def test_bad_table_header_raises(self, dist6, tmp_path):
        bad = tmp_path / "bad.bin"
        with open(bad, "wb") as f:
            f.write(b"XXXX")
            f.write(struct.pack("<I", 0))
        s = CenterSolver4(joint_dist=dist6, table_path=str(bad))
        cube = Cube4.solved()
        cube.apply_move("u")
        with pytest.raises(CenterSolveError):
            s.solve(cube)

    def test_joint_outside_bfs_depth_raises(self, dist6):
        dist2, _ = build_joint_bfs(max_depth=2)
        cube = Cube4.solved()
        cube.apply_moves(["f", "b", "r"])
        r = combined_to_rank(extract_joint(cube))
        assert dist6[r] == 3
        s = CenterSolver4(joint_dist=dist2)
        with pytest.raises(CenterSolveError):
            s.solve(cube)


class TestCancellation:
    def test_cancel_presolved_raises(self, solver):
        ev = threading.Event()
        ev.set()
        with pytest.raises(CenterSolveError):
            solver.solve(Cube4.solved(), cancel_event=ev)

    def test_cancel_during_bfs_raises(self):
        ev = threading.Event()
        ev.set()
        with pytest.raises(CenterSolveError):
            build_joint_bfs(max_depth=10, cancel_event=ev)

    def test_cancel_not_set_succeeds(self, solver):
        ev = threading.Event()
        cube = Cube4.solved()
        cube.apply_moves(["f", "b"])
        assert isinstance(solver.solve(cube, cancel_event=ev), list)


class TestProgress:
    def test_progress_callback_events(self):
        events = []
        build_joint_bfs(max_depth=4, progress_callback=events.append)
        assert [e["depth"] for e in events] == [1, 2, 3, 4]
        keys = {"depth", "frontier", "visited", "transitions", "elapsed", "rate"}
        for e in events:
            assert set(e) == keys


class TestConvenience:
    def test_solve_centers_matches_solver(self, dist6):
        cube = Cube4.solved()
        cube.apply_moves(["f", "r", "u"])
        moves = solve_centers(cube, joint_dist=dist6)
        assert isinstance(moves, list)
        fresh = Cube4.solved()
        fresh.apply_moves(["f", "r", "u"] + moves)
        assert centers_solved(fresh)
