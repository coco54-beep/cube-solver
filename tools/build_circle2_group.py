"""Compile the exact anchored Circle 2 subgroup; SymPy is offline only."""
import heapq
import json
import sys
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sympy.combinatorics import Permutation,PermutationGroup
import numpy as np
from cube.circle_cube import Circle2Cube
from cube.polyhedral import Move,PolyhedralPuzzle
from solver.circle2_group import fingerprint


def inverse(p):
    result=[0]*len(p)
    for i,x in enumerate(p):result[x]=i
    return tuple(result)


def inverse_word(word):return tuple((a,l,-n%4) for a,l,n in reversed(word))


def compact(word):
    out=[]
    for a,l,n in word:
        if out and out[-1][:2]==(a,l):n=(out.pop()[2]+n)%4
        if n:out.append((a,l,n))
    return tuple(out)


def build(kind='circle_2'):
    cube=Circle2Cube() if kind=='circle_2' else PolyhedralPuzzle(kind,3)
    g=cube.geometry;identity=tuple(range(len(g.stickers)))
    pool={g.permutation(Move(a,0,n)):((a,0,n),) for a in range(3 if kind=='circle_2' else 6) for n in (1,2,3)}
    # Match the rigid outer cubies before the repeated single-colour sectors.
    base=sorted(identity,key=lambda i:(-len(g.pieces[g.stickers[i].piece]),i))
    group=PermutationGroup([Permutation(p) for p in pool]);group._schreier_sims(base=base)
    labelled_orbits=[sorted(orbit) for orbit in group.orbits() if len(orbit)>1]
    records=[]
    for level,b in enumerate(group.base):
        gens=dict(pool)
        for p,w in pool.items():
            inv=inverse(p);iw=inverse_word(w)
            if inv not in gens or len(iw)<len(gens[inv]):gens[inv]=iw
        distances={b:0};paths={b:(identity,())};pending=[(0,b)]
        while pending:
            dist,beta=heapq.heappop(pending)
            if distances[beta]!=dist:continue
            p,word=paths[beta]
            for q,qw in gens.items():
                target=q[beta];cost=dist+len(qw)
                if cost>=distances.get(target,float('inf')):continue
                distances[target]=cost;paths[target]=tuple(q[x] for x in p),compact(word+qw)
                heapq.heappush(pending,(cost,target))
        if set(paths)!=set(group.basic_orbits[level]):raise RuntimeError(('Incomplete subgroup',level))
        records.append({str(beta):dict(permutation=p,word=w) for beta,(p,w) in paths.items()})
        if len(paths)==1:
            print(level,1,0,len(pool),flush=True)
            continue
        following={}
        def remember(p,w):
            if p==identity:return
            w=compact(w)
            if p not in following or len(w)<len(following[p]):following[p]=w
        for p,w in pool.items():
            if p[b]==b:remember(p,w)
        inverses={beta:inverse(p) for beta,(p,w) in paths.items()}
        for beta,(p,w) in paths.items():
            for q,qw in gens.items():
                gamma=q[beta];qi=inverses[gamma]
                remember(tuple(qi[q[x]] for x in p),w+qw+inverse_word(paths[gamma][1]))
        # Short outer-cubie moves must not evict all longer generators of
        # the inner-sector kernel. Keep representatives at every remaining
        # stabilizer depth, then fill the rest with the shortest words.
        ordered=sorted(following.items(),key=lambda pair:len(pair[1]))
        # Keep odd/even witnesses on each independent sticker orbit. Without
        # these the shortest 5,000 words can all lie in an even kernel and
        # lose the final coupled swaps. Full basic-orbit agreement above is
        # still mandatory at EVERY level: sampling never certifies a table.
        permutations=np.array([p for p,w in ordered],dtype=np.uint16).reshape(-1,len(identity))
        parities=np.zeros(len(ordered),dtype=np.uint16)
        for bit,orbit in enumerate(labelled_orbits):
            values=permutations[:,orbit];parity=np.zeros(len(ordered),dtype=np.uint16)
            for i in range(len(orbit)-1):
                parity^=(np.count_nonzero(values[:,i,None]>values[:,i+1:],axis=1)&1).astype(np.uint16)
            parities|=parity<<bit
        pool={};buckets={}
        for (p,w),parity in zip(ordered,parities):
            first=next((j for j in range(level+1,len(group.base)) if p[group.base[j]]!=group.base[j]),None)
            key=first,int(parity)
            if first is not None and buckets.get(key,0)<24:
                pool[p]=w;buckets[key]=buckets.get(key,0)+1
        for p,w in ordered[:5000]:pool[p]=w
        print(level,len(paths),max(len(w) for p,w in paths.values()),len(pool),flush=True)
    # Check every word's full permutation and the unchanged anchor on the
    # actual mechanism, not just symbolic multiplication.
    verified=0
    for orbit in records:
        for entry in orbit.values():
            work=Circle2Cube(colors=list(identity)) if kind=='circle_2' else PolyhedralPuzzle(kind,3,list(identity))
            for m in entry['word']:work.apply_move(Move(*m))
            if kind=='circle_2':assert work.anchor==(-1,-1,-1)
            assert tuple(work.colors)==inverse(entry['permutation'])
            verified+=1
    data=dict(version=1,kind=kind,geometry=fingerprint(kind),base=group.base,transversals=records,order=str(group.order()))
    path=Path('solver/data')/('circle2_group.bin' if kind=='circle_2' else kind+'_group.bin')
    path.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('verified',verified,'order',group.order(),'bytes',path.stat().st_size,flush=True)


if __name__=='__main__':
    for kind in sys.argv[1:] or ('circle_2',):build(kind)
