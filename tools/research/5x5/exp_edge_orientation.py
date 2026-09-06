"""5x5 棱的配对一致性（orientation/color-face）分析。

对每条逻辑棱（2 面），其 3 个成员（1 中 + 2 翼）贴的是该两面的颜色。
「配对完成」定义为：3 个成员的 color->face 映射完全一致（同色同面）。

研究问题：
1. 还原态是否天然满足该一致性。
2. 给定两个"同色对"翼，它们放进同槽时能否取向 / 能否出现"翻转不匹配"。
3. 经过打乱（中心已还原）后，逻辑棱的一致比例。
4. 定义规范化棱描述子（canonical edge），用于后续配对调度。
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

def is_middle(pos):
    return sorted(abs(v) for v in pos)==[0,maxc,maxc]

# For an edge piece at pos, return {face: color} for its 2 stickers
def piece_color_face(cubie):
    cf = {}
    for n, col in cubie.stickers.items():
        # normal vector -> face
        # n is a unit axis vector, find face
        f = FACE_BY_AXIS[0][0] if n==(1,0,0) else \
            FACE_BY_AXIS[0][1] if n==(-1,0,0) else \
            FACE_BY_AXIS[1][0] if n==(0,1,0) else \
            FACE_BY_AXIS[1][1] if n==(0,-1,0) else \
            FACE_BY_AXIS[2][0] if n==(0,0,1) else FACE_BY_AXIS[2][1]
        cf[f]=col
    return cf

def edge_consistency(cube):
    """对每条逻辑棱，3 成员是否 color->face 一致。返回 (slot->consistent bool, slot->member_cfmaps)."""
    members = defaultdict(list)
    for pos, cub in cube.cubies.items():
        if len(cub.stickers)==2:
            members[faces_of_pos(pos)].append((pos, cub))
    out = {}
    for slot, mems in members.items():
        fmaps = [tuple(sorted(piece_color_face(c).items())) for _, c in mems]
        out[slot] = (len(set(fmaps)) == 1, fmaps)
    return out

# 1. solved cube consistency
c = Cube5.solved()
ec = edge_consistency(c)
print("solved cube: all consistent?", all(v[0] for v in ec.values()))

# 2. pairing-status distribution over scrambles (centers solved)
GEN = ["R","R'","R2","L","L'","L2","U","U'","U2","D","D'","D2","F","F'","F2","B","B'","B2",
       "2R","2R'","2R2","2L","2L'","2U","2U'","2D","2D'","2F","2F'","2B","2B'","2L2","2U2","2D2","2F2","2B2"]
from solver.center5 import solve_centers5
rng = random.Random(1)
for t in range(5):
    c2 = Cube5.solved()
    c2.apply_moves([rng.choice(GEN) for _ in range(rng.choice([10,20,30]))])
    res = solve_centers5(c2)
    ec2 = edge_consistency(c2)
    consist = sum(1 for v in ec2.values() if v[0])
    print("trial", t, "centers_solved?", res.success, "consistent edges %d/12" % consist)
