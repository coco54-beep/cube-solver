"""Test finite-order two-axis circuits without relaxing material gates."""
import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.pisces import PiscesCube,AXES,ANGLE1,ANGLE2
from cube.polyhedral import Move,dot
from itertools import product
from collections import Counter

started=time.monotonic();angles=(ANGLE1,-ANGLE1,ANGLE2,-ANGLE2);found={};stats=Counter()
for a,b in product(range(12),repeat=2):
    if a==b:continue
    for x,y in product(angles,repeat=2):
        word=(Move(a,0,x),Move(b,0,y));cube=PiscesCube();stats['pairs']+=1
        for repeat in range(1,13):
            try:cube.apply_moves(word)
            except ValueError:stats['blocked']+=1;break
            try:p=cube.aligned_permutation()
            except ValueError:continue
            if p!=tuple(range(len(p))):
                if p not in found or repeat*2<len(found[p]):
                    found[p]=word*repeat
                    print('found',len(found),a,b,x,y,repeat,flush=True)
            break
out=Path('artifacts/research/pisces');out.mkdir(parents=True,exist_ok=True)
(out/'pair-actions.json').write_text(json.dumps([dict(permutation=p,word=[[m.axis,m.layer,m.amount] for m in w]) for p,w in found.items()]),encoding='utf-8')
print('done',stats,len(found),time.monotonic()-started,flush=True)
