"""Offline shortening of Tangram algorithms; uses only universal legal loops."""
from collections import deque
from pathlib import Path
from time import monotonic
import json
import sys
import zlib


def inverse(p):
    result=[0]*len(p)
    for i,v in enumerate(p):result[v]=i
    return result


def cycles(p):
    seen=set();result=[]
    for i in range(len(p)):
        if i in seen or p[i]==i:continue
        current=[];j=i
        while j not in seen:seen.add(j);current.append(j);j=p[j]
        result.append(tuple(current))
    return result


def canonical(c):return min(c,c[1:]+c[:1],c[2:]+c[:2])


def canonical_cycles(cc):
    return tuple(sorted(min(c[i:]+c[:i] for i in range(len(c))) for c in cc))


def invert_word(word):return [[a,l,(-n)%6] for a,l,n in reversed(word)]


def compact(word):
    out=[]
    for a,l,n in word:
        if out and out[-1][0]==a and out[-1][1]==l:
            old=out.pop();n=(n+old[2])%6
        if n:out.append([a,l,n])
    return out


def optimize(kind, source_path=None):
    path=Path(source_path) if source_path else Path('solver/data')/(kind+'_group.bin');table=json.loads(zlib.decompress(path.read_bytes()))
    records=table['strong'];moves=table['moves'];size=table['degree'];begun=monotonic()
    # Small derived algorithms are also useful conjugacy seeds. They are
    # expanded from the same verified basis, never from input fixtures.
    from solver.tangram_table import TangramTable
    source = TangramTable(kind, path)
    for index,record in enumerate(records):
        if record['original'] is not None:continue
        word = source.strong_word(index+1)
        record.pop('shortcut', None)
        if len(word) <= 100:
            record['original'] = len(moves)
            moves.append([[m.axis,m.layer,m.amount] for m in word])
    targets={canonical(c[0]):i for i,r in enumerate(records) if r['original'] is None
             and len(c:=cycles(r['permutation']))==1 and len(c[0])==3}
    short=[(r['permutation'],moves[r['original']]) for r in records if r['original'] is not None and len(moves[r['original']])<=12]
    parents={};queue=deque()
    # Some models have no 3-cycle commutator among their length-three loops.
    # Seed from every existing pure 3-cycle as well, including powers which
    # cancel auxiliary cycles. These are still universal legal algorithms.
    for record in records:
        if record['original'] is None:continue
        p=record['permutation'];current=list(range(size));word=moves[record['original']]
        for exponent in range(1,13):
            current=[p[x] for x in current];cc=cycles(current)
            if not cc:break
            if len(cc)!=1 or len(cc[0])!=3:continue
            key=canonical(cc[0]);candidate=compact(word*exponent)
            old=parents.get(key)
            if old is None:
                parents[key]=(None,candidate);queue.append(key)
            elif len(old[1])>len(candidate):parents[key]=(None,candidate)
    for p,pw in short:
        pi=inverse(p)
        for q,qw in short:
            qi=inverse(q);comm=[qi[pi[q[p[i]]]] for i in range(size)];cc=cycles(comm)
            if len(cc)!=1 or len(cc[0])!=3:continue
            key=canonical(cc[0]);word=compact(pw+qw+invert_word(pw)+invert_word(qw))
            if key in parents:continue
            parents[key]=(None,word);queue.append(key)
    print(kind,'triple targets',len(targets),'seeds',len(queue),flush=True)
    transport=short
    while queue and targets:
        c=queue.popleft()
        if c in targets:
            trace=c;before=[];after=[]
            while parents[trace][0] is not None:
                trace,w=parents[trace];before.append(invert_word(w));after.append(w)
            word=compact([m for w in before for m in w]+parents[trace][1]+[m for w in reversed(after) for m in w])
            records[targets.pop(c)]['shortcut']=word
        for p,word in transport:
            key=canonical(tuple(p[x] for x in c))
            if key in parents:continue
            parents[key]=(c,word);queue.append(key)
        if len(parents)>100000:break
    print('remaining triples',len(targets),'visited',len(parents),'seconds',round(monotonic()-begun,2),flush=True)
    triple_parents=parents
    def triple_word(c):
        trace=canonical(c)
        if trace not in triple_parents:return None
        before=[];after=[]
        while triple_parents[trace][0] is not None:
            trace,w=triple_parents[trace];before.append(invert_word(w));after.append(w)
        return compact([m for w in before for m in w]+triple_parents[trace][1]+[m for w in reversed(after) for m in w])
    for record in records:
        if record['original'] is not None or 'shortcut' in record:continue
        cc=cycles(record['permutation']);transpositions=[(c[0],p) for c in cc for p in c[1:]]
        if len(transpositions)%2:continue
        result=[];valid=True
        for (a,b),(c,d) in zip(transpositions[::2],transpositions[1::2]):
            if {a,b}=={c,d}:continue
            if len({a,b,c,d})==4:triples=((a,c,d),(a,c,b))
            else:
                values={a,b,c,d};p={v:v for v in values}
                for left,right in ((a,b),(c,d)):
                    p={v:right if w==left else left if w==right else w for v,w in p.items()}
                first=min(values);triples=((first,p[first],p[p[first]]),)
            for triple in triples:
                word=triple_word(triple)
                if word is None:valid=False;break
                result+=word
            if not valid:break
        if valid:record['shortcut']=compact(result)
    # The last stabilizer levels often need coupled edge flips. Transport
    # complete small permutations as well as individual three-cycles.
    orbit=list(range(size))
    def find(a):
        while orbit[a]!=a:orbit[a]=orbit[orbit[a]];a=orbit[a]
        return a
    for r in records:
        if r['original'] is None:continue
        for a,b in enumerate(r['permutation']):orbit[find(a)]=find(b)
    def profile(cc):return tuple(sorted((len(c),find(c[0])) for c in cc))
    groups={}
    for i,r in enumerate(records):
        if r['original'] is not None or 'shortcut' in r:continue
        cc=cycles(r['permutation']);groups.setdefault(profile(cc),{})[canonical_cycles(cc)]=i
    power_seeds={signature:{} for signature in groups}
    from math import lcm
    for r in records:
        if r['original'] is None:continue
        p=r['permutation'];order=1
        for c in cycles(p):order=lcm(order,len(c))
        current=list(range(size));original=moves[r['original']]
        for exponent in range(1,min(order,13)):
            current=[p[x] for x in current];cc=cycles(current);signature=profile(cc)
            if signature not in power_seeds:continue
            key=canonical_cycles(cc)
            word=(original*exponent if exponent<=order-exponent else invert_word(original)*(order-exponent))
            old=power_seeds[signature].get(key)
            if old is None or len(old)>len(word):power_seeds[signature][key]=word
    for signature,targets in groups.items():
        parents={};queue=deque()
        for key,word in power_seeds[signature].items():parents[key]=(None,word);queue.append(key)
        for r in records:
            if r['original'] is None:continue
            cc=cycles(r['permutation'])
            if profile(cc)!=signature:continue
            key=canonical_cycles(cc);parents[key]=(None,moves[r['original']]);queue.append(key)
        if not queue:continue
        while queue and targets and len(parents)<30000:
            cc=queue.popleft()
            if cc in targets:
                trace=cc;before=[];after=[]
                while parents[trace][0] is not None:
                    trace,w=parents[trace];before.append(invert_word(w));after.append(w)
                word=compact([m for w in before for m in w]+parents[trace][1]+[m for w in reversed(after) for m in w])
                records[targets.pop(cc)]['shortcut']=word
            for p,word in transport:
                key=canonical_cycles(tuple(tuple(p[x] for x in c) for c in cc))
                if key in parents:continue
                parents[key]=(cc,word);queue.append(key)
        print('profile',signature,'remaining',len(targets),'visited',len(parents),flush=True)
    from functools import lru_cache
    @lru_cache(None)
    def estimated(index):
        record=records[abs(index)-1]
        if 'shortcut' in record:return len(record['shortcut'])
        if record['original'] is not None:return len(moves[record['original']])
        return min(100000,sum(estimated(s) for s in record['product']))
    @lru_cache(None)
    def actual(index):
        record=records[abs(index)-1]
        if index<0:return invert_word(actual(-index))
        if 'shortcut' in record:return record['shortcut']
        if record['original'] is not None:return moves[record['original']]
        return compact([m for s in reversed(record['product']) for m in actual(s)])
    maximum=0
    for i,r in enumerate(records):
        if r['original'] is None and estimated(i+1)<50000:r['shortcut']=actual(i+1);maximum=max(maximum,len(r['shortcut']))
    print('maximum derived word',maximum,flush=True)
    out=Path('artifacts/development')/(kind+'-short-group.bin')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(zlib.compress(json.dumps(table,separators=(',',':')).encode(),9))
    print('saved',len(out.read_bytes()),flush=True)
    return out


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    optimize(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None)
