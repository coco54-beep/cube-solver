import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cube.cube5 import Cube5
from solver.edge5.compact_state import state_of, step, color_off
from solver.edge5.positions import WING_ORDER, MIDDLE_ORDER, COORD_TO_SLOT

SEQ = ["2B", "B2", "F2", "2B'"]


def inv(mv):
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    return mv + "'"


def analyze(seq):
    st = state_of(Cube5.solved())
    for mv in seq:
        st = step(st, mv)
    wp = st.wing
    mp = st.middle
    # wing transpositions
    vis = [False] * 24
    trans = []
    for i in range(24):
        if not vis[i]:
            j = i
            l = []
            while not vis[j]:
                vis[j] = True
                l.append(j)
                j = wp[j]
            if len(l) == 2:
                trans.append(l)
    def wlabel(idx):
        return WING_ORDER[idx]
    def slot_of_idx(idx):
        return COORD_TO_SLOT[WING_ORDER[idx]]
    print("color_off", color_off(st))
    print("middle perm", list(mp))
    print("middle slot map (home slot -> cur slot):")
    for j in range(12):
        h = COORD_TO_SLOT[MIDDLE_ORDER[j]]
        c = COORD_TO_SLOT[MIDDLE_ORDER[mp[j]]]
        if h != c:
            print(f"   {h} -> {c}")
    print("wing transpositions (position pairs -> slots):")
    for l in trans:
        print(f"   wing {wlabel(l[0])} <-> {wlabel(l[1])}  | slots {slot_of_idx(l[0])} <-> {slot_of_idx(l[1])}")
    return st


analyze(SEQ)
