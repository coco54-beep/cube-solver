"""搜索"middle 全部归位 + 翼片上做有用置换"的干净基元。

用 36 个棱位置（24 翼 + 12 中）的置换建模。每动作是一 36 元置换。
BFS 找序列，其 middle 限制必为恒等；记录翼限制，筛出翼 3-cycle 等有用置换。
限制节点数以控制耗时。
"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from collections import deque
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc
import time
d,maxc=get_d_maxc(5)
def is_middle(pos): return sorted(abs(v) for v in pos)==[0,maxc,maxc]
c=Cube5.solved()
edges=sorted(p for p,cu in c.cubies.items() if len(cu.stickers)==2)
idx={p:i for i,p in enumerate(edges)}
MID=[i for i,p in enumerate(edges) if is_middle(p)]
WING=[i for i,p in enumerate(edges) if not is_middle(p)]

GEN=[]
for a in "RLUDFB":
    for s in ("","'","2"): GEN.append(a+s)
for a in "RLUDFB":
    for s in ("","'","2"): GEN.append("2"+a+s)

# position transition: a move maps edges[:] -> new arrangement. Build permutation on indices.
def build_move_perm(mv):
    cc=Cube5.solved()
    cc.apply_move(mv)
    return tuple(idx[cu.home] for p,cu in cc.cubies.items() if len(cu.stickers)==2 and False) if False else None

# Simpler: for each move and each index i (edge position), compute new position index of the piece at edge[i].
# Apply move to solved, get for each edge position p the piece there; its home tells original index.
def move_perm(mv):
    cc=Cube5.solved(); cc.apply_move(mv)
    # piece at edge position j: home index = idx[cu.home]
    perm=[0]*36
    for j,p in enumerate(edges):
        cu=cc.cubies[p]
        perm[j]=idx[cu.home]
    return tuple(perm)

MP={mv:move_perm(mv) for mv in GEN}

def apply_perm(state, perm):
    # state[j] = home index of piece currently at position j. Initial identity.
    # After move: new_position[j] holds the piece that was at perm[j]... 
    # perm[j] = original index of piece now at pos j. state maps position->home.
    # new state: new[j] = state[perm[j]] (piece formerly at position perm[j] moved to j)
    return tuple(state[perm[j]] for j in range(36))

def middle_identity(state):
    return all(state[j]==j for j in MID)
def wing_perm_of(state):
    return {j:state[j] for j in WING}
def wing_cycles(state):
    w=wing_perm_of(state)
    seen=set(); cyc=[]
    for j in WING:
        if j in seen: continue
        l=[]; k=j
        while k not in seen:
            seen.add(k); l.append(k); k=w[k]
        if len(l)>1: cyc.append(l)
    return cyc

start=tuple(range(36))  # identity (all pieces home)
# BFS over sequences, only keep states that could be useful; dedup on full 36-tuple.
# Node cap.
frontier={start:[]}
visited={start}
found=[]
t0=time.time()
goal=None
depth=0
cur={start:[]}
for depth in range(1,13):
    nxt={}
    for st,path in cur.items():
        for mv in GEN:
            ns=apply_perm(st, MP[mv])
            if ns in visited: continue
            visited.add(ns)
            npath=path+[mv]
            nxt[ns]=npath
            if middle_identity(ns) and ns!=start:
                cyc=wing_cycles(ns)
                if any(len(l)==3 for l in cyc) and not any(len(l)==2 for l in cyc):
                    found.append(npath)
                    if goal is None:
                        goal=npath
            if len(visited)>300000:
                break
        if len(visited)>300000: break
    if len(visited)>300000: break
    cur=nxt
    if len(found)>10: break
    if not nxt: break
print("visited", len(visited), "time", round(time.time()-t0,1))
print("middle-clean wing sequences found:", len(found))
for f in found[:10]:
    print("  ", " ".join(f))
