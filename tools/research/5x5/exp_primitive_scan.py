"""候选配对基元调查：能否找到一条只作用翅膀系统、交换两翼位、且保持
middle 与已配对棱的动作。

对 5x5 尝试 4x4 经典 P 的变体（用宽层/外层），考察其：
- 对 24 翼位的置换
- 是否扰动 12 个 middle 位
- 是否保持"已配对"结构（成色对成组移动）
"""
import sys
sys.path.insert(0, r"D:\coco\cube-solver")
from collections import defaultdict
from cube.cube5 import Cube5
from cube.coordinates import get_d_maxc
d, maxc = get_d_maxc(5)
FACE_BY_AXIS = {0:("R","L"),1:("U","D"),2:("F","B")}
def slot(pos):
    fs=[]
    for ax in (0,1,2):
        v=pos[ax]
        if abs(v)==maxc: fs.append(FACE_BY_AXIS[ax][0] if v>0 else FACE_BY_AXIS[ax][1])
    return tuple(sorted(fs))
def is_middle(pos): return sorted(abs(v) for v in pos)==[0,maxc,maxc]

def apply(cube, seq):
    for m in seq: cube.apply_move(m)

def wing_perm(cube, seq):
    s=cube.clone(); apply(s, seq)
    return {p: c.home for p,c in s.cubies.items() if len(c.stickers)==2 and not is_middle(p)}

def middle_moved(cube, seq):
    s=cube.clone(); apply(s,seq)
    return [p for p,c in s.cubies.items() if len(c.stickers)==2 and is_middle(p) and c.pos!=c.home]

def perm_cycles(perm):
    # perm[p]=q ; decompose into cycles of positions
    n=perm if False else None
    seen=set(); cycs=[]
    for p in perm:
        if p in seen: continue
        cyc=[]; q=p
        while q not in seen:
            seen.add(q); cyc.append(q); q=perm[q]
        cycs.append(cyc)
    return cycs

def test_seq(name, seq):
    c=Cube5.solved()
    wp=wing_perm(c, seq)
    movers=[(p,q) for p,q in wp.items() if p!=q]
    mm=middle_moved(c, seq)
    cyc=perm_cycles(wp)
    nonfixed=[cc for cc in cyc if len(cc)>1]
    print("%-22s moves %2d wings, cylens %s, middles moved %d" % (name, len(movers), sorted(len(x) for x in nonfixed), len(mm)))
    return wp, mm

# classic 4x4-ish P with wide u -> 2U or U
cands = {
  "P_u": ["u","R","U","R'","F","R'","F'","R","u'"],
  "P_2U": ["2U","R","U","R'","F","R'","F'","R","2U'"],
  "P_U": ["U","R","U","R'","F","R'","F'","R","U'"],
  "P_2R-ish": ["2R","U","R","U'","B","R","B'","R'","2R'"],
}
for nm,seq in cands.items():
    # 'u' isn't a standard solver token; replace
    pass
# use only legal-ish tokens; test
tests = {
  "2U_RUR'F R'F'R": ["2U","R","U","R'","F","R'","F'","R","2U'"],
  "U_U_RUR'": ["U","R","U","R'","F","R'","F'","R","U'"],
  "2U_RUR'F'": ["2U","R","U","R'","F'","R","U'","R'","2U'"],
  "2R_U2": ["2R","U","R","U'","R'","2R'"],
  "2L_simple": ["2L","U","L","U'","L'","2L'"],
}
for nm,seq in tests.items():
    try:
        test_seq(nm, seq)
    except Exception as e:
        print(nm, "ERR", e)
