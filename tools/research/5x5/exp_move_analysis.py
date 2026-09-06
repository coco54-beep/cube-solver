"""分析单个动作对 wings/middles 的作用，并测试宽层换位子的 middle 清洁性。"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc
d,maxc=get_d_maxc(5)
def is_middle(pos): return sorted(abs(v) for v in pos)==[0,maxc,maxc]

def apply(c, seq):
    for m in seq: c.apply_move(m)

def report(c):
    wm={(p):cu.home for p,cu in c.cubies.items() if len(cu.stickers)==2 and not is_middle(p)}
    mv=[(p,cu.home) for p,cu in c.cubies.items() if len(cu.stickers)==2 and is_middle(p) and cu.pos!=cu.home]
    wmoved=[(p,q) for p,q in wm.items() if p!=q]
    return wmoved, mv

def test(label, seq):
    c=Cube5.solved(); apply(c,seq)
    wm, mv = report(c)
    print("%-16s len%2d  wings_moved %2d  middles_moved %d" % (label, len(seq), len(wm), len(mv)))

# what moves middle edges? only the 12 middle positions.
for m in ["U","R","F","2U","2R","2F","D","L","B","U'"]:
    test("move_"+m, [m])

print("--- commutators of wide/outer ---")
tests={
 "[2U,2R]": ["2U","2R","2U'","2R'"],
 "[2R,2U]": ["2R","2U","2R'","2U'"],
 "[U,2R]": ["U","2R","U'","2R'"],
 "[2R,U2]": ["2R","U2","2R'","U2"],
 "[U,2R2]": ["U","2R2","U'","2R2"],
 "[2U,R]": ["2U","R","2U'","R'"],
 "[2U,2F]": ["2U","2F","2U'","2F'"],
}
for l,s in tests.items():
    test(l, s)
