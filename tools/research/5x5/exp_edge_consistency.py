"""验证：5x5 配棱是否退化为纯位置问题（无独立朝向翻面）。

对每个色对（12 个），其唯一 home 棱。若其 2 片翼同为该对且都位于 home 棱的
2 个翼位，则该棱自动一致（color->face 同）。若每次都是自动一致，则说明
翼片朝向固定、两翼无翻面差异，配棱只需"把对的两翼放到 home 棱"。

同时验证 middle 同理：色对的中块位于其 home 中位时自动一致。
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
            if n[ax]!=0:
                cf[FACE_BY_AXIS[ax][0] if n[ax]>0 else FACE_BY_AXIS[ax][1]]=col
    return cf

GEN=["R","R'","R2","L","L'","L2","U","U'","U2","D","D'","D2","F","F'","F2","B","B'","B2",
     "2R","2R'","2R2","2L","2L'","2U","2U'","2D","2D'","2F","2F'","2B","2B'","2L2","2U2","2D2","2F2","2B2"]
rng=random.Random(11)
# For each random scramble, for every edge, check consistency of its 3 members.
# Then test: is it possible for a color-pair's 2 wings to be both in THEIR HOME edge but inconsistent?
# Count occurrences and consistency.
edge_consistent_always=0; edge_inconsistent=0; both_home=0
for t in range(30):
    c=Cube5.solved(); c.apply_moves([rng.choice(GEN) for _ in range(25)])
    members=defaultdict(list)
    for pos,cub in c.cubies.items():
        if len(cub.stickers)==2:
            members[slot(pos)].append((pos,cub))
    for s, mems in members.items():
        fmaps=[tuple(sorted(color_face(cu).items())) for _,cu in mems]
        cons=(len(set(fmaps))==1)
        if cons: edge_consistent_always+=1
        else: edge_inconsistent+=1
print("edges: consistent", edge_consistent_always, "inconsistent", edge_inconsistent)

# Determine if wings-only consistency matters: for each color pair, are its 2 wings always mutually compatible?
# The 2 wings of a color pair: when placed in the SAME slot faces, are they same color-face map?
# Equivalent check: in ALL scrambles, whenever a slot holds BOTH wings of the pair that its color defines,
# it's consistent. We already know orientation is piece-fixed; verify inversion never happens.
# Direct: build a "canonical" wing orientation invariant and check the 2 wings of a pair are never "opposite".
wings_by_pair=defaultdict(list)
for t in range(30):
    c=Cube5.solved(); c.apply_moves([rng.choice(GEN) for _ in range(25)])
    for pos,cub in c.cubies.items():
        if len(cub.stickers)==2 and not is_middle(pos):
            wings_by_pair[frozenset(cub.stickers.values())].append((pos,cub,color_face(cub)))
# check: within a color pair, do the 2 wings ever have "opposite" orientation?
# define orientation of a wing relative to its own position's faces
opposite=0; compatible=0
for pair,wings in wings_by_pair.items():
    # there should be exactly 2 wings per color-pair set collected across scrambles (accumulates)
    pass
# Instead directly: for a given color pair, the 2 wings should always be the exact same physical piece type.
# Verify distinct physical wing identities per color pair = exactly 2 and they are orientation-identical.
# We'll compute a per-color-pair canonical orientation from wing's color->sticker-direction.
from collections import Counter
orient_counter=Counter()
for pair,wings in wings_by_pair.items():
    # each entry (pos,cub,cf). canonical orientation: map each color to its sticker DIRECTION sign vector
    for pos,cub,cf in wings:
        # direction signature: for the wing body, which color is on +X vs its complementary
        # Build set of (color, normal) sorted
        sig=frozenset((col, n) for n,col in cub.stickers.items())
        orient_counter[(tuple(sorted(pair)), sig)]+=1
print("distinct wing signatures per color-pair (should be 1 per pair if no flip):")
sigs=defaultdict(set)
for pair,wings in wings_by_pair.items():
    for pos,cub,cf in wings:
        sig=frozenset((col,n) for n,col in cub.stickers.items())
        sigs[tuple(sorted(pair))].add(sig)
print({k:len(v) for k,v in sigs.items()})
