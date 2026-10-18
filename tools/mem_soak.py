"""Continuous-use memory soak: switch puzzle families and solve repeatedly."""
import gc
import sys
import time

import psutil

from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.conversion import cubies_to_facelets
from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble, scramble_length
from solver.polyhedral import solve_polyhedral
from solver.solver3 import solve_3x3
from solver.solver4 import solve_4x4

PROC = psutil.Process()


def rss_mb():
    return PROC.memory_info().rss / (1024 * 1024)


def cache_entries():
    total = 0
    per = []
    for name, module in list(sys.modules.items()):
        if not module:
            continue
        for attr in list(vars(module)):
            try:
                value = getattr(module, attr)
                info = getattr(value, "cache_info", None)
            except Exception:
                continue
            if callable(info):
                try:
                    size = info().currsize
                except Exception:
                    continue
                if size:
                    total += size
                    per.append((size, f"{name}.{attr}"))
    per.sort(reverse=True)
    return total, per[:5]


def case_cube3():
    cube = Cube3.solved()
    cube.apply_moves(["R", "U", "F'", "L2"])
    result = solve_3x3(cubies_to_facelets(cube.cubies, 3))
    assert result.success


def case_cube4():
    cube = Cube4.solved()
    cube.apply_moves(["R", "U", "F'", "2R"])
    result = solve_4x4(cube)
    assert result.success


def case_poly(kind, n):
    def run():
        cube = PolyhedralPuzzle.solved(kind, n)
        cube.colors = [s.face for s in cube.geometry.stickers]
        scramble(cube, min(24, scramble_length(cube)), seed=7)
        solution = solve_polyhedral(cube)
        check = cube.clone()
        for move in solution:
            check.apply_move(move)
        assert check.is_solved(), kind
    return run


CASES = [
    ("cube3", case_cube3),
    ("cube4", case_cube4),
    ("megaminx3", case_poly("megaminx", 3)),
    ("megaminx5", case_poly("megaminx", 5)),
    ("football3", case_poly("football", 3)),
    ("icosahedron3", case_poly("icosahedron", 3)),
    ("moyu5", case_poly("moyu", 5)),
    ("pyraminx3", case_poly("pyraminx", 3)),
    ("skewb3", case_poly("skewb", 3)),
    ("pentahedron3", case_poly("pentahedron", 3)),
]


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    gc.collect()
    baseline = rss_mb()
    print(f"baseline {baseline:.1f} MB")
    for r in range(1, rounds + 1):
        t0 = time.perf_counter()
        for name, fn in CASES:
            fn()
            gc.collect()
        entries, top = cache_entries()
        print(f"round {r}: {time.perf_counter()-t0:5.1f}s  "
              f"rss={rss_mb():7.1f} MB  (+{rss_mb()-baseline:6.1f})  "
              f"lru_entries={entries}  top={top}")


if __name__ == "__main__":
    main()
