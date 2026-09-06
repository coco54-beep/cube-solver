"""随机搜索短序列，找到"翼限制为单个 3-cycle"的基元并记载 middle 效果。"""
import sys, random
sys.path.insert(0, r"D:\coco\cube-solver")
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc
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
    return tuple(idx[cu.home] for p in edges for cu in [cc.cubies[p]])
def apply_perm(state,perm):
    return tuple(state[perm[j]] for j in range(36))
def wing_cycles(state):
    w={j:state[j] for j in WING}
    seen=set();cyc=[]
    for j in WING:
        if j in seen:continue
        l=[];k=j
        while k not in seen:
            seen.add(k);l.append(k);k=w[k]
        if len(l)>1:cyc.append(l)
    return cyc
def middle_moved(state): return [j for j in MID if state[j]!=j]
MP={mv:move_perm(mv) for mv in GEN}
rng=random.Random(0)
# random walk sequences, look for wing 3-cycle
best=[]
for trial in range(40000):
    n=rng.randint(3,7)
    seq=[rng.choice(GEN) for _ in range(n)]
    st=tuple(range(36))
    for mv in seq: st=apply_perm(st,MP[mv])
    wc=wing_cycles(st)
    if len(wc)==1 and len(wc[0])==3:
        mm=middle_moved(st)
        print("found len",n,"mid_moved",len(mm),"seq"," ".join(seq))
        best.append((seq,wc,mm))
        if len(best)>=12: break
print("total found", len(best))
