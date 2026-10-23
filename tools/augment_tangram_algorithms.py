"""Find small universal commutators before shortening the Tangram table."""
import sys
import json
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from solver.tangram_table import TangramTable,compact
from tools.optimize_tangram_tables import cycles,inverse


def augment(kind, source_path=None):
    table=TangramTable(kind,source_path);degree=table.degree
    seeds={tuple(r['permutation']): table.strong_word(i+1) for i,r in enumerate(table.records)
           if len(table.strong_word(i+1))<=100}
    transports=[(p,w) for p,w in seeds.items() if len(w)<=12]
    conjugates=dict(seeds)
    for p,word in list(seeds.items()):
        if len(word)>40:continue
        for g,gw in transports:
            gi=inverse(g)
            q=tuple(gi[p[g[i]]] for i in range(degree))
            qw=compact(gw+word+tuple(m.inverse(6) for m in reversed(gw)))
            if q not in conjugates or len(qw)<len(conjugates[q]):conjugates[q]=qw
    candidates=list(conjugates.items())
    extras={}
    print('conjugates',len(candidates),flush=True)
    for i,(p,pw) in enumerate(candidates):
        pi=inverse(p);ps={j for j,v in enumerate(p) if j!=v}
        for q,qw in candidates[i+1:]:
            if not any(q[j]!=j for j in ps):continue
            qi=inverse(q)
            comm=tuple(qi[pi[q[p[j]]]] for j in range(degree))
            cc=cycles(comm)
            if not cc or sum(map(len,cc))>8:continue
            word=compact(pw+qw+tuple(m.inverse(6) for m in reversed(pw))+tuple(m.inverse(6) for m in reversed(qw)))
            old=extras.get(comm)
            if old is None or len(word)<len(old):extras[comm]=word
    path=Path(source_path) if source_path else Path('solver/data')/(kind+'_group.bin');data=json.loads(zlib.decompress(path.read_bytes()))
    known={tuple(r['permutation']) for r in data['strong']}
    parents=list(range(degree))
    def find(a):
        while parents[a]!=a:parents[a]=parents[parents[a]];a=parents[a]
        return a
    for p in seeds:
        for a,b in enumerate(p):parents[find(a)]=find(b)
    profiles={}
    count=0
    for p,word in sorted(extras.items(),key=lambda item:len(item[1])):
        if p in known:continue
        profile=tuple(sorted((len(c),find(c[0])) for c in cycles(p)))
        if profiles.get(profile,0)>=4:continue
        profiles[profile]=profiles.get(profile,0)+1
        data['strong'].append(dict(permutation=list(p),original=len(data['moves']),product=[]))
        data['moves'].append([[m.axis,m.layer,m.amount] for m in word]);known.add(p);count+=1
    out=Path('artifacts/development')/(kind+'-augmented-group.bin')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('extra algorithms',count,'pure triples',sum(len(cycles(p))==1 and len(cycles(p)[0])==3 for p in extras),flush=True)
    return out


if __name__=='__main__':augment(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None)
