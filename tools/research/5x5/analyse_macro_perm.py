import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cube.cube5 import Cube5
from solver.edge5.compact_state import state_of, _SLOT_WINGS, _SLOT_MID
from solver.edge5.free_slice import member_slots
from solver.edge5.compact_state import WING_ORDER, MIDDLE_ORDER, _POS_HOME_SLOT
from solver.edge5.positions import WING_INDEX, MIDDLE_INDEX, slot

M = ["2U", "F'", "U'", "F", "2U'"]
c = Cube5.solved()
c.apply_moves(M)
st = state_of(c)

# wing: position -> piece home idx. Print which home slots' wings went where.
print("wing perm (home_slot -> new_slot) for each wing position:")
for i in range(24):
    pos = WING_ORDER[i]          # position index i
    piece_home_slot = _POS_HOME_SLOT[WING_ORDER[st.wing[i]]]
    pos_slot = _POS_HOME_SLOT[pos]
    if piece_home_slot != pos_slot:
        print(f"   pos_slot {pos_slot} (wing@{pos})  <- piece from {piece_home_slot}")

print("middle perm (slot -> new position slot):")
for i in range(12):
    pos = MIDDLE_ORDER[i]
    piece_home_slot = _POS_HOME_SLOT[MIDDLE_ORDER[st.middle[i]]]
    pos_slot = _POS_HOME_SLOT[pos]
    if piece_home_slot != pos_slot:
        print(f"   pos_slot {pos_slot} <- middle from {piece_home_slot}")
