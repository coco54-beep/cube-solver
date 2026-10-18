"""Microbenchmark permutation application on a large polyhedral state."""
import time

import numpy as np

from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import inverse

cube = PolyhedralPuzzle("megaminx", 13)
cube.colors = [s.face for s in cube.geometry.stickers]
move = cube.moves()[0]
perm = cube.geometry.permutation(move)
inv = inverse(perm)
colors = list(cube.colors)
n = len(colors)
arr = np.asarray(colors, dtype=np.int16)
inv_np = np.asarray(inv, dtype=np.intp)
LOOPS = 3000


def bench(name, fn):
    t0 = time.perf_counter()
    for _ in range(LOOPS):
        fn()
    dt = (time.perf_counter() - t0) / LOOPS
    print(f"{name:28s} {dt*1e6:8.1f} us")


def current():
    result = [0] * n
    for source, destination in enumerate(perm):
        result[destination] = colors[source]
    return result


def comp_inv():
    return [colors[source] for source in inv]


def map_inv():
    return tuple(map(colors.__getitem__, inv))


def np_convert():
    return np.asarray(colors, dtype=np.int16)[inv_np].tolist()


def np_keep():
    return arr[inv_np]


bench("current loop", current)
bench("list comp (inv)", comp_inv)
bench("tuple(map getitem)", map_inv)
bench("numpy asarray+gather+tolist", np_convert)
bench("numpy gather (keep array)", np_keep)
