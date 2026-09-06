"""5x5 翼的朝向（orientation）分析。

问题：同色对的两片翼能否总是"朝向兼容"地放进同一逻辑棱槽？
对逻辑棱 {A,B}，其成员须满足 color->face 一致。翼片在移动过程中，其内在的
两色到两 sticker 方向的指派随旋转变化。这里考察：是否存在两个同为色对 {c1,c2}
的翼，它们在槽中呈现出"翻转不兼容"（即无法和 middle 一起构成一致棱）。

方法：打乱后，枚举每个色对（12 个），取其 2 片翼，比较它们的相对朝向；
若一片可以经"原地翻转"匹配另一片（即两片的 color->face 指派为互补），
则说明翼存在朝向自由度（pairing 时必须处理翻转）。
"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from collections import defaultdict
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc, FACE_NORMALS
import random

d, maxc = get_d_maxc(5)
FACE_BY_AXIS = {0: ("R","L"), 1: ("U","D"), 2: ("F","B")}
def faces_of_pos(pos):
    fs=[]
    for ax in (0,1,2):
        v=pos[ax]
        if abs(v)==maxc: fs.append(FACE_BY_AXIS[ax][0] if v>0 else FACE_BY_AXIS[ax][1])
    return tuple(sorted(fs))

def color_face(cubie):
    # map each face to the color of the sticker pointing at it
    cf={}
    for n,col in cubie.stickers.items():
        f = None
        for ax in (0,1,2):
            if n[ax]!=0:
                f = FACE_BY_AXIS[ax][0] if n[ax]>0 else FACE_BY_AXIS[ax][1]
        cf[f]=col
    return cf

def rel_orient(cf, slot):
    # given a color-face map and target slot {A,B}, return the assignment (color on A, color on B) normalized
    a,b = slot
    return (cf.get(a), cf.get(b))

GEN = ["R","R'","R2","L","L'","L2","U","U'","U2","D","D'","D2","F","F'","F2","B","B'","B2",
       "2R","2R'","2R2","2L","2L'","2U","2U'","2D","2D'","2F","2F'","2B","2B'","2L2","2U2","2D2","2F2","2B2"]
rng=random.Random(3)
# Test: in a scrambled cube, for each color-pair, place its 2 wings conceptually into the two
# wing slots of their home logical edge and check consistency.
# We instead examine: do the 2 wings of a color-pair, when put into the SAME slot, always match orientation?
# Because a slot only "wants" one color-face map, we check the intrinsic flip-invariance.
for t in range(4):
    c=Cube5.solved(); c.apply_moves([rng.choice(GEN) for _ in range(25)])
    # group all 24 wings by color pair
    bypair=defaultdict(list)
    for pos,cub in c.cubies.items():
        if len(cub.stickers)==2:
            # only wings (skip middle)
            if sorted(abs(v) for v in pos)==[0,maxc,maxc]: continue
            bypair[frozenset(cub.stickers.values())].append((pos,cub))
    print("--- trial", t)
    for pair,members in sorted(bypair.items()):
        if len(members)!=2: 
            print("  pair", sorted(pair), "has", len(members), "wings (!!)"); continue
        (p1,c1),(p2,c2)=members
        cf1=color_face(c1); cf2=color_face(c2)
        # slot of each wing
        s1=faces_of_pos(p1); s2=faces_of_pos(p2)
        # normalized assignment for each (color on 1st face, color on 2nd face) using slot's face order
        # Use fixed slot face order (sorted). identity of colors.
        # Does c1 and c2 have the same color->face relative to faces_of their positions?
        # Determine "flip" by comparing the two colors in a fixed canonical slot frame.
        a1,b1=s1; a2,b2=s2
        # For consistency in a slot, when both wings land in SAME logical edge, need same map.
        # Since they're the same color pair {cA,cB} with cA!=cB, they match iff for the target slot
        # the color placed on a given face is the same.
        # The min thing we can check: does piece orientation allow flip? i.e., among the two wings of a pair
        # is their color->sticker-direction assignment related by a physical rotation that maps one wing position
        # to a different slot, not merely reflection.
        print("   pair",sorted(pair),"w1 at",p1,"slot",s1,"cf",cf1,"| w2 at",p2,"slot",s2,"cf",cf2)
        break
    break
