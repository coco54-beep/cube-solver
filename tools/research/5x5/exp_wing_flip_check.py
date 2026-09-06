"""决定性验证：色对的两片翼，若同处其 home 棱的翼位，该棱是否恒一致。

对每片翼，其"目标色对" = 其两色的 frozenset。对每个棱槽 {A,B}，home 色对 =
{color_A, color_B}。统计：凡"该槽两个翼位都放了 home 色对的翼"的槽，其
3 成员是否恒一致。若恒一致 => 两翼同视同向、无翻面差 => 配棱为纯位置问题。
"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from collections import defaultdict
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc, FACE_NORMALS
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
# face -> color mapping for home pair determination
def face_color(cube):
    # color on each face from a single face center
    fc={}
    for n,col in cube.cubies.items():
        pass
    return fc

GEN=["R","R'","R2","L","L'","L2","U","U'","U2","D","D'","D2","F","F'","F2","B","B'","B2",
     "2R","2R'","2R2","2L","2L'","2U","2U'","2D","2D'","2F","2F'","2B","2B'","2L2","2U2","2D2","2F2","2B2"]
rng=random.Random(17)

# Fixed face colors from solved cube
solved=Cube5.solved()
FACE_COLOR={}
for pos,cub in solved.cubies.items():
    if len(cub.stickers)==1:
        for n,col in cub.stickers.items():
            for ax in (0,1,2):
                if n[ax]!=0: FACE_COLOR[FACE_BY_AXIS[ax][0] if n[ax]>0 else FACE_BY_AXIS[ax][1]]=col

home_pair_of={}
for a in FACE_COLOR:
    for b in FACE_COLOR:
        if a<b:
            home_pair_of[frozenset((FACE_COLOR[a],FACE_COLOR[b]))]=(a,b)

tot_slots=0; wtih_homepair=0; consistent_when_homepair=0; inconsistent_when_homepair=0
for t in range(40):
    c=Cube5.solved(); c.apply_moves([rng.choice(GEN) for _ in range(25)])
    members=defaultdict(list)
    for pos,cub in c.cubies.items():
        if len(cub.stickers)==2: members[slot(pos)].append((pos,cub))
    for s,mems in members.items():
        # home pair for this slot faces
        cA,cB=FACE_COLOR[s[0]],FACE_COLOR[s[1]]
        hp=frozenset((cA,cB))
        wings=[(p,cu) for p,cu in mems if not is_middle(p)]
        mid=[cu for p,cu in mems if is_middle(p)]
        # check: are the 2 wings' color pair == hp?
        if len(wings)==2 and all(frozenset(cu.stickers.values())==hp for _,cu in wings):
            wtih_homepair+=1
            fmaps=[tuple(sorted(color_face(cu).items())) for _,cu in mems]
            if len(set(fmaps))==1: consistent_when_homepair+=1
            else: inconsistent_when_homepair+=1
print("slots where both wings are home-pair:", wtih_homepair)
print("  consistent:", consistent_when_homepair, " inconsistent:", inconsistent_when_homepair)
