"""随机搜索短序列，找到"middle 限制为单个 3-cycle"的基元（记载其翼效果）。"""
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
def apply_perm(state,perm): return tuple(state[perm[j]] for j in range(36))
def cycles_of(fixed_idx, state):
    w={j:state[j] for j in fixed_idx}
    seen=set();cyc=[]
    for j in fixed_idx:
        if j in seen:continue
        l=[];k=j
        while k not in seen:
            seen.add(k);l.append(k);k=w[k]
        if len(l)>1:cyc.append(l)
    return cyc
MP={mv:move_perm(mv) for mv in GEN}
rng=random.Random(5)
best=[]
for trial in range(30000):
    n=rng.randint(3,8)
    seq=[rng.choice(GEN) for _ in range(n)]
    st=tuple(range(36))
    for mv in seq: st=apply_perm(st,MP[mv])
    mc=cycles_of(MID,st)
    if len(mc)==1 and len(mc[0])==3:
        wc=cycles_of(WING,st)
        print("mid3 len",n,"wings_cycles",[len(x) for x in wc],"seq"," ".join(seq))
        best.append((seq,mc,wc))
        if len(best)>=10: break
print("total",len(best))
