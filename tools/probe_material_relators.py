"""Recover short floating-piece tools from exact mechanical quotient relations."""
import sys,json
from pathlib import Path
from collections import Counter
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.suncube_aligned import AlignedSunCube,generators,source_key
from cube.polyhedral import Move
from solver.polyhedral import simplify,inverse_word,apply_word
from tools.exact_group_certificate import Certificate
from tools.weighted_group_builder import build


def run():
    cube=AlignedSunCube();g=cube.geometry;n=len(cube.colors);I=np.arange(n,dtype=np.int32)
    atoms=[np.asarray(a,dtype=np.int32) for a,w in generators()];left=set(range(n));orbits=[]
    while left:
        o={min(left)};queue=list(o)
        for s in queue:
            for p in atoms:
                if int(p[s]) not in o:o.add(int(p[s]));queue.append(int(p[s]))
        orbits.append(tuple(sorted(o)));left-=o
    leaf=[o for o in orbits if all(len(g.pieces[g.stickers[s].piece])==1 for s in o)
          and min(Counter(g.stickers[s].face for s in o).values())>=2]
    core=tuple(s for o in orbits if o not in leaf for s in o);ids={s:i for i,s in enumerate(core)}
    pool={tuple(ids[int(p[s])] for s in core):((i,0,1),) for i,p in enumerate(atoms)}
    base=sorted(range(len(core)),key=lambda i:(-len(g.pieces[g.stickers[core[i]].piece]),-core[i]))
    cert=Certificate(len(core),base)
    for p in pool:cert.add(p)
    def compact(w):return tuple((m.axis,m.layer,m.amount) for m in simplify(tuple(Move(*a) for a in w),2))
    def backwards(w):return tuple(reversed(w))
    found={};seen=set();counts=[0];kernel={}
    def relation(w):
        if len(w)>128 or w in seen:return
        seen.add(w);p=I
        for axis,layer,amount in w:
            if amount%2:p=atoms[axis][p]
        counts[0]+=1
        for i,o in enumerate(leaf):
            changed=[s for s in o if p[s]!=s]
            if changed and (i not in kernel or (len(changed),len(w))<(kernel[i]['support'],len(kernel[i]['word']))):
                kernel[i]=dict(slots=o,support=len(changed),word=w)
                print('KERNEL',i,len(changed),len(w),flush=True)
            if len(changed)!=3:continue
            a=min(changed);trip=(a,int(p[a]),int(p[p[a]]))
            if len(set(trip))!=3 or p[trip[-1]]!=a:continue
            if i not in found or len(w)<len(found[i]['word']):
                found[i]=dict(slots=o,base=trip,word=w)
                print('RELATOR',i,len(w),'seen',counts[0],flush=True)
    rows=build(pool,base,[tuple(r) for r in cert.trans],(),compact,backwards,
               preserve_group=True,limit=100,bucket_limit=100,on_relation=relation,
               report=lambda *r:print(*r,flush=True))
    target=Path('artifacts/research/suncube/quotient-relators.json');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(dict(source=source_key(),cycles=list(found.values()),kernel=list(kernel.values())),separators=(',',':')),encoding='utf-8')
    print('SAVED',target,'orbits',len(found),'relations',counts[0],flush=True)


if __name__=='__main__':run()
