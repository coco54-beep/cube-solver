import sys, random, itertools
sys.path.insert(0, r"D:\coco\cube-solver")
from cube.cube5 import Cube5
from solver.center5.orbits import CenterOrbitKind, kind_of_position
from solver.center5.primitives import CENTER_ORDER, CENTER_INDEX, CORNER_MAIN, EDGE_MAIN
from solver.center5.conjugation import conjugate_cycle


def edge_centers_fixed(cube):
    for p, x in cube.cubies.items():
        if len(x.stickers) == 1 and kind_of_position(x.home) == CenterOrbitKind.EDGE:
            if p != x.home:
                return False
    return True


corner_ids = [i for i in range(len(CENTER_ORDER))
              if kind_of_position(CENTER_ORDER[i]) == CenterOrbitKind.CORNER]
print("num corner ids:", len(corner_ids))
rng = random.Random(1)
dirty = 0; total = 0
for _ in range(200):
    target = rng.sample(corner_ids, 3)
    c = Cube5.solved()
    try:
        c.apply_moves(conjugate_cycle(CORNER_MAIN, target))
    except ValueError:
        continue
    total += 1
    if not edge_centers_fixed(c):
        dirty += 1
        if dirty <= 5:
            print("DIRTY corner conj target", target)
print(f"dirty {dirty}/{total} for corner conjugates")
