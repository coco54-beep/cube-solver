"""找"翼 3-cycle"基元：短序列使翼限制为单个 3-cycle（并记录其 middle 效果）。

若存在"翼纯 3-cycle"，即可像中心解法那样经共轭做任意翼排布/配棱。
这里不要求 middle 归位，而是记载它=单独 3-cycle（便于后配或作为控制变量）。
"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
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
def move_perm(mv):
    cc=Cube5.solved(); cc.apply_move(mv)
    return tuple(idx[cu.home] for j,p in enumerate(edges) for cu in [cc.cubies[p]])
def apply_perm(state, perm):
    return tuple(state[perm[j]] for j in range(36))

def wing_cycles(state):
    w={j:state[j] for j in WING}
    seen=set(); cyc=[]
    for j in WING:
        if j in seen: continue
        l=[];k=j
        while k not in seen:
            seen.add(k);l.append(k);k=w[k]
        if len(l)>1: cyc.append(l)
    return cyc
def middle_moved(state):
    return [j for j in MID if state[j]!=j]

MP={mv:move_perm(mv) for mv in GEN}
# BFS up to depth 8, find first states where wing restriction == single 3-cycle.
start=tuple(range(36))
visited={start}
cur={start:[]}
t0=time.time()
found=[]
for depth in range(1,9):
    nxt={}
    for st,path in cur.items():
        for mv in GEN:
            ns=apply_perm(st,MP[mv])
            if ns in visited: continue
            visited.add(ns)
            np=path+[mv]
            nxt[ns]=np
            wc=wing_cycles(ns)
            if len(wc)==1 and len(wc[0])==3:
                found.append((np, wing_cycles(ns), middle_moved(ns)))
                if len(found)>=8: break
        if len(found)>=8: break
    if len(found)>=8: break
    cur=nxt
    if not nxt: break
print("found wing-3cycles:", len(found), "time", round(time.time()-t0,1))
for path, wc, mm in found:
    print("  seq len", len(path), "mid_moved", len(mm), ":", " ".join(path))
