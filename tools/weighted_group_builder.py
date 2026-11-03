"""Offline short-word stabilizer transversals with exact orbit checks."""
import heapq
import numpy as np


def inverse(p):
    out=[0]*len(p)
    for i,x in enumerate(p):out[x]=i
    return tuple(out)


def build(pool,base,expected_orbits,point_orbits,compact,inverse_word,report=None,limit=5000,
          preserve_group=False,bucket_limit=None,on_relation=None):
    if bucket_limit is not None and (type(bucket_limit) is not int or bucket_limit<=0 or not preserve_group):
        raise ValueError('Bounded parity buckets require exact group preservation')
    degree=len(next(iter(pool)));identity=tuple(range(degree));records=[]
    point_orbits=[sorted(orbit) for orbit in point_orbits if len(orbit)>1]
    if len(point_orbits)>64:raise ValueError('Orbit parity mask is too narrow')
    mask_dtype=np.uint16 if len(point_orbits)<=16 else np.uint64
    for level,b in enumerate(base):
        gens=dict(pool)
        for p,w in pool.items():
            inv=inverse(p);iw=inverse_word(w)
            if inv not in gens or len(iw)<len(gens[inv]):gens[inv]=iw
        distances={b:0};paths={b:(identity,())};queue=[(0,b)]
        while queue:
            dist,beta=heapq.heappop(queue)
            if distances[beta]!=dist:continue
            p,w=paths[beta]
            for q,qw in gens.items():
                target=q[beta];cost=dist+len(qw)
                if cost>=distances.get(target,float('inf')):continue
                distances[target]=cost;paths[target]=tuple(q[x] for x in p),compact(w+qw)
                heapq.heappush(queue,(cost,target))
        if set(paths)!=set(expected_orbits[level]):raise ValueError(('Incomplete stabilizer',level,len(paths),len(expected_orbits[level])))
        records.append({str(beta):dict(permutation=p,word=w) for beta,(p,w) in paths.items()})
        if len(paths)==1:
            if report:report(level,1,0,len(pool))
            continue
        following={}
        def remember(p,w):
            w=compact(w)
            if p==identity:
                if on_relation and w:on_relation(w)
                return
            if on_relation and p in following and w!=following[p]:
                on_relation(compact(w+inverse_word(following[p])))
            if p not in following or len(w)<len(following[p]):following[p]=w
        for p,w in pool.items():
            if p[b]==b:remember(p,w)
        inverses={beta:inverse(p) for beta,(p,w) in paths.items()}
        for beta,(p,w) in paths.items():
            for q,qw in gens.items():
                gamma=q[beta];qi=inverses[gamma]
                remember(tuple(qi[q[x]] for x in p),w+qw+inverse_word(paths[gamma][1]))
        ordered=sorted(following.items(),key=lambda item:len(item[1]))
        permutations=np.array([p for p,w in ordered],dtype=np.uint16).reshape(-1,degree)
        masks=np.zeros(len(ordered),dtype=mask_dtype)
        for bit,orbit in enumerate(point_orbits):
            values=permutations[:,orbit];parity=np.zeros(len(ordered),dtype=mask_dtype)
            for i in range(len(orbit)-1):
                parity^=(np.count_nonzero(values[:,i,None]>values[:,i+1:],axis=1)&1).astype(mask_dtype)
            masks|=parity<<bit
        pool={};buckets={}
        for (p,w),mask in zip(ordered,masks):
            first=next((j for j in range(level+1,len(base)) if p[base[j]]!=base[j]),None)
            key=first,int(mask)
            if (first is not None and buckets.get(key,0)<24
                    and (bucket_limit is None or len(pool)<bucket_limit)):
                pool[p]=w;buckets[key]=buckets.get(key,0)+1
        pool.update(ordered[:limit])
        if preserve_group and len(pool)<len(following) and level+1<len(base):
            # Orbit/parity buckets alone are a word-length heuristic, not a
            # certificate that discarded generators are redundant. Preserve
            # the complete next stabilizer before advancing to another base
            # point. This matters for layered prisms with coupled orbits.
            from tools.exact_group_certificate import Certificate
            import math
            expected=math.prod(len(o) for o in expected_orbits[level+1:])
            # Certify using a small independent generating set. Feeding the
            # thousands of redundant short words to Schreier-Sims directly
            # is needlessly expensive for higher-order prisms.
            retained=Certificate(degree,base[level+1:]);order=1
            # Sparse generators expose independent leaf factors first. Starting
            # from the shortest dense moves repeatedly reconstructs the entire
            # coupled action and can also discard useful short late-stage tools.
            candidates=sorted(ordered,key=lambda item:(sum(i!=x for i,x in enumerate(item[0])),len(item[1])))
            for p,w in candidates:
                if order==expected:break
                if not retained.add(p):continue
                pool[p]=w;order=retained.order
                if order>expected or expected%order:
                    raise ValueError(('Unexpected stabilizer order',level,order,expected))
            if order!=expected:raise ValueError(('Incomplete exact stabilizer',level,order,expected))
        if report:report(level,len(paths),max(len(w) for p,w in paths.values()),len(pool))
    return records
