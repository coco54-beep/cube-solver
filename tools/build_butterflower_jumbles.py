"""Offline full-material certification of Butterflower's closed petal moves."""
import sys,json,zlib
from pathlib import Path
from itertools import combinations,product
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.butterflower import ButterflowerCube,JUMBLE
from cube.butterflower_material import AXES,fingerprint
from cube.polyhedral import Move,dot


def build():
    root=ButterflowerCube();found={}
    for target,normal in enumerate(AXES[:12]):
        adjacent=[i for i,n in enumerate(AXES[:12]) if abs(dot(n,normal)-.5)<1e-8]
        for a,b in combinations(adjacent,2):
            if dot(AXES[a],AXES[b])>-.49:continue
            for sa,sb in product((-1,1),repeat=2):
                word=(Move(a,0,sa*JUMBLE),Move(b,0,sb*JUMBLE),Move(target,0,180.),
                      Move(b,0,-sb*JUMBLE),Move(a,0,-sa*JUMBLE))
                try:
                    work=root.clone().apply_moves(word);action=work.aligned_permutation()
                except ValueError:continue
                if any(action[action[i]]!=i for i in range(len(action))):raise ValueError('Non-involution')
                if work.apply_moves(word).signature()!=root.signature():raise ValueError('Interior did not close')
                found.setdefault(action,word)
        print('certified axis',target,'distinct exchanges',len(found),flush=True)
    data=dict(version=1,source=fingerprint(),rows=[dict(action=p,word=[[m.axis,m.layer,m.amount] for m in w]) for p,w in found.items()])
    target=Path(__file__).resolve().parents[1]/'cube/data/butterflower_jumbles.bin'
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print(target,len(found),target.stat().st_size,flush=True)


if __name__=='__main__':build()
