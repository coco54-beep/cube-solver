"""搜索"middle 归位 + 恰好交换两片翼"的配对基元。

对从 solved 出发的短动作序列，筛选出满足：
  - 12 个 middle 全部回到 home
  - 24 片中恰有 2 片翼移动（且为一次换位）
该类序列即"干净翼交换"基元；经 setup 共轭可交换任意两翼位，用于配棱。
"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from collections import deque
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc
d, maxc = get_d_maxc(5)
def is_middle(pos): return sorted(abs(v) for v in pos)==[0,maxc,maxc]
GENP=[]  # moves
for a in "RLUDFB": 
    for s in ("","'"): 
        GENP.append(a+s)
for a in "RLUDFB":
    for s in ("","'"):
        GENP.append("2"+a+s)
# also rotations? x y z move middles around too; allow them? keep to layer moves.

def state_mid(cube):
    return tuple(p for p,cu in cube.cubies.items() if len(cu.stickers)==2 and is_middle(p) and cu.pos!=cu.home)

def wings_perm(cube):
    m={}
    for p,cu in cube.cubies.items():
        if len(cu.stickers)==2 and not is_middle(p):
            m[p]=cu.home
    return m

# BFS up to depth 12
start=Cube5.solved()
found=[]
q=deque()
q.append((start.clone(), []))
seen={start:0}
# we'll do a bounded BFS but state is huge; instead do DFS-ish iterative deepening
import itertools
# Use order: limit search to sequences (we'll just do BFS but keep reachable states limited)
# Better: iterative deepening DFS on sequence tree, check each node.
found_list=[]
def dfs(cube, seq):
    if len(seq)>12: return
    mm=state_mid(cube)
    if not mm:
        wp=wings_perm(cube)
        moved=[(p,q) for p,q in wp.items() if p!=q]
        if len(moved)==2:
            found_list.append(list(seq))
            return
    for m in GENP:
        c2=cube.clone(); c2.apply_move(m)
        dfs(c2, seq+[m])
try:
    dfs(start, [])
except RecursionError:
    pass
print("found clean 2-wing-swap primitives (length<=12):", len(found_list))
for f in found_list[:40]:
    print("  ", " ".join(f))
