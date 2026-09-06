"""追踪 case0：打乱+中心还原还原后，打开2R，UR三块逐位置追踪。
"""
import os, sys
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
import random
from cube.cube5 import Cube5
from solver.center5 import solve_centers5
from solver.edge5.compact_state import state_of
from solver.edge5.free_slice import member_slots
from solver.edge5.positions import SLOT_NAMES
MOVES = ["U","D","L","R","F","B","U'","D'","L'","R'","F'","B'","2U","2D","2L","2R","2F","2B","2U'","2D'","2L'","2R'","2F'","2B'"]
def scramble(cube, length, rng):
    prev=None
    for _ in range(length):
        mv=rng.choice(MOVES)
        while prev and mv.lstrip('0123456789')[0]==prev.lstrip('0123456789')[0]:
            mv=rng.choice(MOVES)
        cube.apply_move(mv); prev=mv
rng=random.Random(11)
c=Cube5.solved(); scramble(c,4,rng); cr=solve_centers5(c); c.apply_moves(cr.moves)
t=next((s for s in SLOT_NAMES if not __import__('solver.edge5.state',fromlist=['is_edge_paired']).is_edge_paired(c,s)),'UF')
print('target',t)
for label,mv in [('initial',None),('open 2R','2R'),('F','F'),('close 2R\'',"2R'")]:
    if mv: c.apply_move(mv)
    ms,wa,wb=member_slots(state_of(c),t)
    print(f"{label:12s} 中={ms} 翼a={wa} 翼b={wb}")
