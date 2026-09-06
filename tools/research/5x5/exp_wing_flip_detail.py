"""深入考察：为何"两翼均为 home 色对"的槽仍可能不一致。区分三种成因：
  (a) 两翼彼此朝向不同（一翼翻转）—— 视作"翼翻转问题"
  (b) 该槽 middle 不是 home 色对的中块
  (c) 其它
统计各成因占比，并给出一个具体反例。
"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from collections import defaultdict
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc
import random
d,maxc=get_d_maxc(5)
FACE_BY_AXIS={0:("R","L"),1:("U","D"),2:("F","B")}
def slot(pos):
    fs=[]
    for ax in (0,1,2):
        v=pos[ax]
        if abs(v)==maxc: fs.append(FACE_BY_AXIS[ax][0] if v>0 else FACE_BY_AXIS[ax][1])
    return tuple(sorted(fs))
def is_middle(pos): return sorted(abs(v) for v in pos)==[0,maxc,maxc]
def color_face(cub):
    cf={}
    for n,col in cub.stickers.items():
        for ax in (0,1,2):
            if n[ax]!=0: cf[FACE_BY_AXIS[ax][0] if n[ax]>0 else FACE_BY_AXIS[ax][1]]=col
    return cf
solved=Cube5.solved()
FACE_COLOR={}
for pos,cub in solved.cubies.items():
    if len(cub.stickers)==1:
        for n,col in cub.stickers.items():
            for ax in (0,1,2):
                if n[ax]!=0: FACE_COLOR[FACE_BY_AXIS[ax][0] if n[ax]>0 else FACE_BY_AXIS[ax][1]]=col

GEN=["R","R'","R2","L","L'","L2","U","U'","U2","D","D'","D2","F","F'","F2","B","B'","B2",
     "2R","2R'","2R2","2L","2L'","2U","2U'","2D","2D'","2F","2F'","2B","2B'","2L2","2U2","2D2","2F2","2B2"]
rng=random.Random(23)

causes=defaultdict(int); total=0
examples=[]
for t in range(120):
    c=Cube5.solved(); c.apply_moves([rng.choice(GEN) for _ in range(30)])
    members=defaultdict(list)
    for pos,cub in c.cubies.items():
        if len(cub.stickers)==2: members[slot(pos)].append((pos,cub))
    for s,mems in members.items():
        cA,cB=FACE_COLOR[s[0]],FACE_COLOR[s[1]]
        hp=frozenset((cA,cB))
        wings=[(p,cu) for p,cu in mems if not is_middle(p)]
        mid=[cu for p,cu in mems if is_middle(p)]
        if len(wings)==2 and all(frozenset(cu.stickers.values())==hp for _,cu in wings):
            total+=1
            # wing consistency alone
            wmaps=[tuple(sorted(color_face(cu).items())) for _,cu in wings]
            wings_agree=(len(set(wmaps))==1)
            # middle is home pair? and its map
            mid_ok = len(mid)==1 and frozenset(mid[0].stickers.values())==hp
            fullmaps=[tuple(sorted(color_face(cu).items())) for _,cu in mems]
            full_cons=(len(set(fullmaps))==1)
            if not full_cons:
                if not wings_agree: causes["wings_flip"]+=1
                else: causes["middle_mismatch"]+=1
                if len(examples)<3:
                    examples.append((s, wmaps, mid_ok, [tuple(sorted(color_face(m).items())) for m in mid]))
print("total home-pair-wing slots:", total, "causes:", dict(causes))
for e in examples:
    print("  slot", e[0], "wingmaps", e[1], "midhomepair?", e[2], "midmaps", e[3])
