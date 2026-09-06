"""在真实 Cube5 上验证候选基元并精确记录其 W/M 行为。

验证：
1. `B U' 2B' U`（中等 3-cycle）：记录 middle 3-cycle 的具体位置，以及翼的效果。
2. 用还原态重放校验：施加后是否仍为"每条棱 3 成员一致"（联动是否守恒）。
"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from collections import defaultdict
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc
d,maxc=get_d_maxc(5)
FACE_BY_AXIS={0:("R","L"),1:("U","D"),2:("F","B")}
def slot(pos):
    fs=[]
    for ax in (0,1,2):
        v=pos[ax]
        if abs(v)==maxc: fs.append(FACE_BY_AXIS[ax][0] if v>0 else FACE_BY_AXIS[ax][1])
    return tuple(sorted(fs))
def is_middle(pos): return sorted(abs(v) for v in pos)==[0,maxc,maxc]

c=Cube5.solved()
seq=["B","U'","2B'","U"]
r=c.clone()
for m in seq: r.apply_move(m)
# record middle & wing moves
mov=[(p,cu.home) for p,cu in r.cubies.items() if len(cu.stickers)==2 and is_middle(p) and cu.pos!=cu.home]
wm=[(p,cu.home) for p,cu in r.cubies.items() if len(cu.stickers)==2 and not is_middle(p) and cu.pos!=cu.home]
print("middle moves:", mov)
print("wing moves:", len(wm))

# edge consistency preserved? (all logical edges still all-same member)
def edge_consistency(cube):
    members=defaultdict(list)
    for pos,cub in cube.cubies.items():
        if len(cub.stickers)==2: members[slot(pos)].append(cub)
    out={}
    for s,mems in members.items():
        fm=[tuple(sorted((f,col) for n,col in cu.stickers.items() for f in [slot_from_face(n)])) for cu in mems]
        out[s]=(len(set(fm))==1)
    return out
def slot_from_face(n):
    for ax in (0,1,2):
        if n[ax]!=0: return FACE_BY_AXIS[ax][0] if n[ax]>0 else FACE_BY_AXIS[ax][1]
f0=edge_consistency(Cube5.solved())
f1=edge_consistency(r)
print("solved all consistent:", all(f0.values()))
print("after prim all consistent:", all(f1.values()))
# which slots changed
for s in f0:
    if f0[s]!=f1[s]:
        print("  slot",s,"became",f1[s])
