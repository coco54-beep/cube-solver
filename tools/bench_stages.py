"""Per-orbit move breakdown for long polyhedral solutions."""
import json
import sys
import time

from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble, scramble_length
from solver.polyhedral import solve_polyhedral
from solver.polyhedral_reduction import begin_stage_trace, end_stage_trace


def main():
    kind, n = sys.argv[1], int(sys.argv[2])
    cube = PolyhedralPuzzle.solved(kind, n)
    cube.colors = [s.face for s in cube.geometry.stickers]
    scramble(cube, scramble_length(cube), seed=12345)
    trace = begin_stage_trace()
    t0 = time.perf_counter()
    solution = solve_polyhedral(cube)
    elapsed = time.perf_counter() - t0
    log = end_stage_trace() or []
    summary = {
        "kind": kind, "n": n, "seconds": round(elapsed, 3),
        "moves": len(solution), "orbit_words": len(log),
        "orbit_moves": sum(item["moves"] for item in log),
        "top": sorted(log, key=lambda item: -item["moves"])[:12],
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
