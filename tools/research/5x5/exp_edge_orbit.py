"""5x5 棱位置在合法动作（外层 + 两层宽转）下的轨道与朝向分析。

1. 36 个棱位置的轨道划分（union-find，用 apply_to_pos 作用）。
2. 各轨道内 middle / wing 构成。
3. 每条逻辑棱的槽位自转方向（各成员朝向的相对关系）。
4. 目标配对关系定义。
"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from collections import defaultdict, deque
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc
from solver.center5.legal_moves import LEGAL_5X5_CENTER_MOVES
from solver.center5.orbits import apply_to_pos

GEN = list(LEGAL_5X5_CENTER_MOVES)  # 36 moves (outer+2wide x '',',2)
d, maxc = get_d_maxc(5)

c = Cube5.solved()
edges = [p for p, cub in c.cubies.items() if len(cub.stickers) == 2]

FACE_BY_AXIS = {0: ("R","L"), 1: ("U","D"), 2: ("F","B")}
def edges_faces(pos):
    fs=[]
    for ax in (0,1,2):
        v=pos[ax]
        if abs(v)==maxc:
            fs.append(FACE_BY_AXIS[ax][0] if v>0 else FACE_BY_AXIS[ax][1])
    return tuple(sorted(fs))
def classify(pos):
    mags=sorted(abs(v) for v in pos)
    return "middle" if mags==[0,maxc,maxc] else "wing"  # [-3?,...]

# union-find orbits under GEN
parent={p:p for p in edges}
def find(a):
    while parent[a]!=a:
        parent[a]=parent[parent[a]]; a=parent[a]
    return a
def union(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: parent[ra]=rb
for p in edges:
    for m in GEN:
        np=apply_to_pos(p, m, 5)
        if np in parent: union(p,np)
groups=defaultdict(list)
for p in edges: groups[find(p)].append(p)
print("=== orbits of 36 edge positions under all legal moves ===")
print("orbit count:", len(groups))
for root, grp in sorted(groups.items(), key=lambda kv:-len(kv[1])):
    kinds=set(classify(p) for p in grp)
    slots=set(edges_faces(p) for p in grp)
    print("  size", len(grp), "kinds", kinds, "#slots", len(slots))

# Now separate orbits: use only OUTER moves vs only 2WIDE
print("\n=== orbits under OUTER only ===")
OUT=[m for m in GEN if not m.startswith("2")]
def orbits(gen):
    parent={p:p for p in edges}
    def find(a):
        while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
        return a
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[ra]=rb
    for p in edges:
        for m in gen:
            np=apply_to_pos(p,m,5)
            if np in parent: union(p,np)
    g=defaultdict(list)
    for p in edges: g[find(p)].append(p)
    return g
o=orbits(OUT)
print("  count", len(o))
for root,grp in sorted(o.items(), key=lambda kv:-len(kv[1])):
    print("   size", len(grp), "kinds", set(classify(p) for p in grp))
print("\n=== orbits under 2WIDE only ===")
W=[m for m in GEN if m.startswith("2")]
o2=orbits(W)
print("  count", len(o2))
for root,grp in sorted(o2.items(), key=lambda kv:-len(kv[1])):
    print("   size", len(grp), "kinds", set(classify(p) for p in grp))
