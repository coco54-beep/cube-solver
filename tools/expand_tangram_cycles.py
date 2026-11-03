"""Expand reusable small-cycle transports before building stabilizer paths."""
import heapq,json,zlib
from pathlib import Path
from solver.tangram_table import TangramTable,compact
from tools.optimize_tangram_tables import cycles,inverse


def expand(kind,source_path,max_cost=80):
    table=TangramTable(kind,source_path);degree=table.degree
    seed={tuple(r['permutation']):table.strong_word(i+1) for i,r in enumerate(table.records)}
    from sympy.combinatorics import Permutation,PermutationGroup
    group=PermutationGroup([Permutation(p) for p in seed])
    orbit_size={a:len(orbit) for orbit in group.orbits() for a in orbit}
    def small(p):
        cc=cycles(p);profile=sorted(map(len,cc))
        return (profile in ([3],[2,2]) or
                (profile==[3,3] and all(orbit_size[c[0]]<=6 for c in cc)))
    transports=[(p,w,tuple(inverse(p)),tuple(m.inverse(6) for m in reversed(w)))
                for p,w in seed.items() if len(w)<=12]
    best={};pending=[];serial=0
    for p,w in seed.items():
        if len(w)>max_cost:continue
        q=tuple(range(degree))
        for exponent in range(1,min(12,max_cost//max(1,len(w)))+1):
            q=tuple(p[a] for a in q)
            if not small(q):continue
            word=compact(w*exponent)
            if q in best and len(best[q])<=len(word):continue
            best[q]=word;heapq.heappush(pending,(len(word),serial,q));serial+=1
    while pending:
        cost,_,p=heapq.heappop(pending);w=best[p]
        if cost!=len(w):continue
        for g,gw,gi,back in transports:
            if cost+2*len(gw)>max_cost:continue
            q=tuple(gi[p[g[i]]] for i in range(degree))
            candidate=compact(gw+w+back)
            if q in best and len(best[q])<=len(candidate):continue
            best[q]=candidate;heapq.heappush(pending,(len(candidate),serial,q));serial+=1
    data=json.loads(zlib.decompress(Path(source_path).read_bytes()))
    for p,w in best.items():
        data['strong'].append(dict(permutation=list(p),original=len(data['moves']),product=[]))
        data['moves'].append([[m.axis,m.layer,m.amount] for m in w])
    out=Path('artifacts/development')/(kind+'-cycles-group.bin')
    out.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('small-cycle library',len(best),'max cost',max(map(len,best.values()),default=0),flush=True)
    return out
