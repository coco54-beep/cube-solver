"""Offline exact subgroup of the three free faces of a canonical Fused Cube."""
import heapq
import json
import sys
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sympy.combinatorics import Permutation,PermutationGroup
from solver.bandaged_state import model


def inverse(p):
    out=[0]*len(p)
    for i,x in enumerate(p):out[x]=i
    return tuple(out)


def inverse_word(word):
    return tuple(m if m.endswith('2') else m[:-1] if m.endswith("'") else m+"'" for m in reversed(word))


def compact(word):
    out=[]
    for move in word:
        count=2 if move.endswith('2') else 3 if move.endswith("'") else 1
        if out and out[-1][0]==move[0]:
            old=out.pop();count=(count+(2 if old.endswith('2') else 3 if old.endswith("'") else 1))%4
        if count:out.append(move[0]+{1:'',2:'2',3:"'"}[count])
    return tuple(out)


def build():
    geometry=model('fused_cube');base=geometry.base
    atoms=[(h,normal,color) for h,c in sorted(base.cubies.items()) for normal,color in sorted(c.stickers.items())]
    slots={(h,n):i for i,(h,n,c) in enumerate(atoms)}
    identities={(h,c):i for i,(h,n,c) in enumerate(atoms)}
    identity=tuple(range(len(atoms)));pool={};permutations=[]
    for token in geometry.moves:
        cube=base.clone();cube.apply_move(token)
        p=[0]*len(atoms)
        for cubie in cube.cubies.values():
            for normal,color in cubie.stickers.items():p[identities[cubie.home,color]]=slots[cubie.pos,normal]
        permutations.append(Permutation(p));pool[tuple(p)]=(token,)
    group=PermutationGroup(permutations);group._schreier_sims(base=list(range(len(atoms))))
    expected=group.basic_orbits;chosen_base=group.base
    records=[]
    for level,b in enumerate(chosen_base):
        gens=dict(pool)
        for p,word in pool.items():
            inv=inverse(p);iw=inverse_word(word)
            if inv not in gens or len(iw)<len(gens[inv]):gens[inv]=iw
        distances={b:0};paths={b:(identity,())};queue=[(0,b)]
        while queue:
            dist,beta=heapq.heappop(queue)
            if distances[beta]!=dist:continue
            p,word=paths[beta]
            for g,gw in gens.items():
                target=g[beta];cost=dist+len(gw)
                if cost>=distances.get(target,float('inf')):continue
                distances[target]=cost;paths[target]=tuple(g[x] for x in p),compact(word+gw)
                heapq.heappush(queue,(cost,target))
        if set(paths)!=set(expected[level]):raise RuntimeError(('Incomplete stabilizer',level,len(paths),len(expected[level])))
        records.append({str(beta):dict(permutation=p,word=w) for beta,(p,w) in paths.items()})
        following={}
        def remember(p,word):
            if p==identity:return
            word=compact(word)
            if p not in following or len(word)<len(following[p]):following[p]=word
        for p,word in pool.items():
            if p[b]==b:remember(p,word)
        inverses={beta:inverse(p) for beta,(p,w) in paths.items()}
        for beta,(p,word) in paths.items():
            for g,gw in gens.items():
                gamma=g[beta];gi=inverses[gamma]
                remember(tuple(gi[g[x]] for x in p),word+gw+inverse_word(paths[gamma][1]))
        pool=dict(sorted(following.items(),key=lambda item:len(item[1]))[:5000])
        print(level,len(paths),max(len(w) for p,w in paths.values()),len(pool),flush=True)
    data=dict(version=1,kind='fused_cube',geometry=geometry.fingerprint,
              atoms=atoms,base=chosen_base,transversals=records,order=str(group.order()))
    # Every word is generated from legal fixed free faces. Independently
    # check its complete sticker permutation on the actual grid mechanism.
    count=0
    for orbit in records:
        for item in orbit.values():
            cube=base.clone();cube.apply_moves(item['word']);p=[0]*len(atoms)
            for cubie in cube.cubies.values():
                for normal,color in cubie.stickers.items():p[identities[cubie.home,color]]=slots[cubie.pos,normal]
            assert p==list(item['permutation']);count+=1
    path=Path('solver/data/fused_group.bin')
    path.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('verified',count,'order',group.order(),'bytes',path.stat().st_size,flush=True)


if __name__=='__main__':build()
