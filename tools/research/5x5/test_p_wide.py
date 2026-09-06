import sys
sys.path.insert(0, ".")
from cube.cube5 import Cube5
from solver.edge5.compact_state import state_of, step, color_off, MOVES

inner = ["R", "U", "R", "F", "R", "F", "R"]


def co(seq):
    st = state_of(Cube5.solved())
    for mv in seq:
        st = step(st, mv)
    return color_off(st)


def inv(mv):
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    return mv + "'"


wide = [m for m in MOVES if m[:1].isdigit()]
for w in wide:
    seq = [w] + inner + [inv(w)]
    print("WIDE", w, "color_off", co(seq))
