"""Benchmark polyhedral solvers: wall time, total moves, per-stage timing."""
import json
import sys
import time

from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble, scramble_length
from solver.polyhedral import solve_polyhedral


def main():
    kind = sys.argv[1]
    n = int(sys.argv[2])
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 12345
    cube = PolyhedralPuzzle.solved(kind, n)
    cube.colors = [s.face for s in cube.geometry.stickers]
    length = scramble_length(cube)
    scramble(cube, length, seed=seed)
    original = cube.clone()
    stages = []
    t0 = time.perf_counter()
    cpu0 = time.process_time()
    solution = solve_polyhedral(
        cube, progress=lambda a, b: stages.append([a, b, time.perf_counter() - t0]))
    elapsed = time.perf_counter() - t0
    cpu_elapsed = time.process_time() - cpu0
    replay = original.clone()
    for move in solution:
        replay.apply_move(move)
    print(json.dumps({
        "kind": kind, "n": n, "sticker_count": len(cube.colors),
        "scramble_length": length, "seconds": round(elapsed, 3),
        "cpu_seconds": round(cpu_elapsed, 3),
        "moves": len(solution), "replay_ok": replay.is_solved(),
        "stages": [[a, b, round(t, 3)] for a, b, t in stages],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
