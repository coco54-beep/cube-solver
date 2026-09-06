"""5x5 棱（edge）位置模型探索。

在还原态 Cube5 上枚举 36 个棱块（贴 2 面），按坐标绝对值分类：
    - middle：恰好 2 个坐标为 ±maxc(6)，第三坐标为 0  （棱中心）
    - wing  ：恰好 2 个坐标为 ±6，第三坐标为 ±3       （左右两翼）
并按两条「面」聚合成 12 条逻辑棱。
"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc, FACE_AXIS_SIGN

d, maxc = get_d_maxc(5)
print("d", d, "maxc", maxc)

c = Cube5.solved()
edges = [p for p, cub in c.cubies.items() if len(cub.stickers) == 2]
print("edge count", len(edges))

def face_of_axis(axis, sign):
    return FACE_AXIS_SIGN  # axis->(pos_name, neg_name)

# map axis sign -> face letter
def faces_of(pos):
    fs = []
    for ax, v in enumerate(pos):
        if abs(v) == maxc:
            fs.append("RLUDFB"[[0,1,2][ax]*2 + (0 if v>0 else 1)])  # placeholder
    return fs

# Build face-by-axis directly
FACE_BY_AXIS = {0: ("R","L"), 1: ("U","D"), 2: ("F","B")}
def edges_faces(pos):
    fs = []
    for ax in (0,1,2):
        v = pos[ax]
        if abs(v) == maxc:
            fs.append(FACE_BY_AXIS[ax][0] if v>0 else FACE_BY_AXIS[ax][1])
    return tuple(sorted(fs))

def classify(pos):
    mags = sorted(abs(v) for v in pos)
    if mags == [0, maxc, maxc]:
        return "middle"
    if mags == [3, maxc, maxc]:
        return "wing"
    return "unknown:" + str(mags)

from collections import defaultdict
model = defaultdict(lambda: {"middle": [], "wing": []})
for p in sorted(edges):
    slot = edges_faces(p)
    model[slot][classify(p)].append(p)

print("\n=== logical edges (%d) ===" % len(model))
for slot in sorted(model):
    m = model[slot]
    print(slot, "middle", m["middle"], "wings", sorted(m["wing"]))

wc = sum(len(v["wing"]) for v in model.values())
mc = sum(len(v["middle"]) for v in model.values())
print("total wings", wc, "total middles", mc)
