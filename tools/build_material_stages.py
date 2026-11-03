"""Certify a small colour quotient plus independent singleton three-cycles."""
import sys,json,zlib,math
from pathlib import Path
from time import monotonic
from collections import Counter
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import Move
from solver.polyhedral import simplify,inverse_word,apply_word
from solver.lattice_data import geometry_key
from solver.polyhedral_reduction import Transports
from tools.exact_group_certificate import Certificate
from tools.weighted_group_builder import build


def run(sun=False):
    butter='--butterflower' in sys.argv
    master='--master-clover' in sys.argv
    flower='--flower' in sys.argv
    twins_reference='--twins-pcubes' in sys.argv
    fourteen='--helicopter-14' in sys.argv
    if fourteen:from cube.helicopter_14_aligned import AlignedHelicopter14 as Factory,generators,source_key
    elif twins_reference:from cube.twins_pcubes_aligned import AlignedTwinsPCubes as Factory,generators,source_key
    elif master:from cube.master_clover_aligned import AlignedMasterClover as Factory,generators,source_key
    elif butter:from cube.butterflower_aligned import AlignedButterflower as Factory,generators,source_key
    elif flower:from cube.flower_copter_aligned import AlignedFlowerCopter as Factory,generators,source_key
    elif sun:from cube.suncube_aligned import AlignedSunCube as Factory,generators,source_key
    else:from cube.twins_cad_reduced import AlignedReducedTwins as Factory,generators,source_key
    started=monotonic();cube=Factory();g=cube.geometry;degree=len(cube.colors);order=g.spec.turn_order
    atoms=tuple((np.asarray(a,dtype=np.int32),((i,0,g.spec.step(i)),)) for i,(a,w) in enumerate(generators()))
    invs=tuple(np.argsort(p) for p,w in atoms);identity=np.arange(degree,dtype=np.int32)
    def compact(w):return tuple((m.axis,m.layer,m.amount) for m in simplify(tuple(Move(*a) for a in w),order))
    def backwards(w):return tuple((m.axis,m.layer,m.amount) for m in inverse_word(tuple(Move(*a) for a in w),order))
    left=set(range(degree));orbits=[]
    while left:
        orbit={min(left)};queue=list(orbit)
        for beta in queue:
            for p,w in atoms:
                gamma=int(p[beta])
                if gamma not in orbit:orbit.add(gamma);queue.append(gamma)
        orbits.append(tuple(sorted(orbit)));left-=orbit
    owner={s:i for i,o in enumerate(orbits) for s in o};near={};cycles={};small={};leaf_tools={}
    singleton=np.asarray([len(g.pieces[s.piece])==1 for s in g.stickers])
    def inspect(p,w):
        support=np.flatnonzero(p!=identity)
        if not len(support):return
        if len(support)<=12:small.setdefault(tuple(map(int,p)),w)
        if singleton[support].all():leaf_tools.setdefault(tuple(map(int,p)),w)
        if len(support)!=3 or not singleton[support].all():return
        i=owner[int(support[0])]
        if any(owner[int(s)]!=i for s in support):return
        orbit=orbits[i];counts=Counter(g.stickers[s].face for s in orbit)
        if min(counts.values())<2:return
        first=int(support[0]);trip=(first,int(p[first]),int(p[p[first]]))
        if len(set(trip))!=3 or p[trip[-1]]!=first:return
        current=cycles.get(i)
        if current is None or len(w)<len(current[0]):cycles[i]=w,trip
    for i,(a,aw) in enumerate(atoms):
        for j,(b,bw) in enumerate(atoms):
            p=invs[j][invs[i][b[a]]];support=np.flatnonzero(p!=identity)
            if len(support) and len(support)<=32:
                w=compact(aw+bw+backwards(aw)+backwards(bw));near.setdefault(p.tobytes(),(p,w));inspect(p,w)
    for a,aw in near.values():
        ai=np.argsort(a)
        for j,(b,bw) in enumerate(atoms):
            p=invs[j][ai[b[a]]]
            if np.count_nonzero(p!=identity)<=72:
                inspect(p,compact(aw+bw+backwards(aw)+backwards(bw)))
    if sun:
        # Short relations of the mechanical quotient can be nontrivial
        # five-cycles of a floating leaf orbit. Turn a five-cycle and a
        # conjugate into a certified three-cycle, rather than expanding an
        # enormous labelled stabilizer word for these interchangeable leaves.
        mechanical=tuple(s for o in orbits if any(not singleton[s] for s in o)
                         or min(Counter(g.stickers[s].face for s in o).values())<2 for s in o)
        local={s:i for i,s in enumerate(mechanical)}
        source=Path('artifacts/research/suncube/quotient-relators.json')
        if not source.exists():
            from tools.probe_material_relators import run as discover_relations
            discover_relations()
        relations=json.loads(source.read_text(encoding='utf-8'))
        if relations['source']!=source_key():raise ValueError('Stale mechanical quotient relations')
        for row in relations.get('cycles',())+relations.get('kernel',()):
            raw=tuple(tuple(m) for m in row['word'])
            lifted=np.asarray(apply_word(g,tuple(Move(*m) for m in raw)),dtype=np.int32)
            if any(lifted[s]!=s for s in mechanical):raise ValueError('Quotient relation changes the mechanical core')
            inspect(lifted,raw)
            support=tuple(s for s in row['slots'] if lifted[s]!=s)
            if len(support) not in (4,5):continue
            root=tuple(sorted(support));parents={root:None};queue=[root];hit=None
            for state in queue:
                for j,(shift,sw) in enumerate(atoms):
                    child=tuple(sorted(int(shift[s]) for s in state))
                    if child in parents:continue
                    parents[child]=(state,j);queue.append(child)
                    if len(set(root)&set(child))==1:hit=child;break
                if hit is not None:break
            if hit is None:raise ValueError('Kernel tool cannot reach an overlap of one')
            path=[]
            while parents[hit] is not None:hit,j=parents[hit];path.append(j)
            sw=tuple(m for j in reversed(path) for m in atoms[j][1])
            shift=np.asarray(apply_word(g,tuple(Move(*m) for m in sw)),dtype=np.int32)
            conjugate=np.argsort(shift)[lifted[shift]];li=np.argsort(lifted);ci=np.argsort(conjugate)
            comm=ci[li[conjugate[lifted]]];cw=compact(sw+raw+backwards(sw))
            inspect(comm,compact(raw+cw+backwards(raw)+backwards(cw)))
        for a,aw in atoms:
            for b,bw in atoms:
                p=b[a];q=[local[int(p[s])] for s in mechanical];seen=set();power=1
                for start in range(len(q)):
                    if start in seen:continue
                    size=0;j=start
                    while j not in seen:seen.add(j);j=q[j];size+=1
                    power=math.lcm(power,size)
                if power>15:continue
                lifted=identity
                for _ in range(power):lifted=p[lifted]
                support=np.flatnonzero(lifted!=identity)
                if len(support)!=5 or not singleton[support].all():continue
                raw=compact((aw+bw)*power);li=np.argsort(lifted)
                for j,(shift,sw) in enumerate(atoms):
                    conjugate=invs[j][lifted[shift]];ci=np.argsort(conjugate)
                    comm=ci[li[conjugate[lifted]]]
                    if np.count_nonzero(comm!=identity)!=3:continue
                    cw=compact(sw+raw+backwards(sw))
                    inspect(comm,compact(raw+cw+backwards(raw)+backwards(cw)))
                target=owner[int(support[0])]
                if target in cycles:continue
                # A transported five-cycle sharing exactly one work position
                # with the first gives a three-cycle. Search only the 5-set,
                # rather than a full coloured puzzle or a labelled group.
                root=tuple(map(int,support));parents={root:None};queue=[root];hit=None
                for state in queue:
                    for j,(shift,sw) in enumerate(atoms):
                        child=tuple(sorted(int(shift[s]) for s in state))
                        if child in parents:continue
                        parents[child]=(state,j);queue.append(child)
                        if len(set(root)&set(child))==1:hit=child;break
                    if hit is not None:break
                if hit is None:raise ValueError('Leaf five-cycle transport did not reach an overlap of one')
                path=[]
                while parents[hit] is not None:
                    hit,j=parents[hit];path.append(j)
                sw=tuple(m for j in reversed(path) for m in atoms[j][1])
                shift=np.asarray(apply_word(g,tuple(Move(*m) for m in sw)),dtype=np.int32)
                conjugate=np.argsort(shift)[lifted[shift]];ci=np.argsort(conjugate)
                comm=ci[li[conjugate[lifted]]];cw=compact(sw+raw+backwards(sw))
                inspect(comm,compact(raw+cw+backwards(raw)+backwards(cw)))
    if not flower and not sun and not butter and not master and not twins_reference and not fourteen:
        source=Path('artifacts/research/twins-cad/quotient-relators.json')
        if source.exists():
            saved=json.loads(source.read_text(encoding='utf-8'))
            from cube.twins_cad_material import fingerprint
            if saved['source']!=fingerprint():raise ValueError('Stale Twins CAD leaf tools')
            for record in saved['cycles']:
                raw=record['word']
                word=tuple(tuple(m) for m in raw)
                action=np.asarray(apply_word(g,tuple(Move(*m) for m in word)),dtype=np.int32)
                support=np.flatnonzero(action!=identity)
                if len(support)!=3 or not singleton[support].all():continue
                inspect(action,word)
    if flower:
        # These short relations were extracted from our full, independently
        # certified action group. Recheck their effect before using them to
        # remove interchangeable single-colour pieces from the quotient.
        source=Path('artifacts/research/flower-copter/leaf-tools-dwg.json')
        if source.exists():
            saved=json.loads(source.read_text(encoding='utf-8'))
            if saved['source']!=source_key():raise ValueError('Stale Flower leaf relations')
            for raw in saved['tools']:
                word=tuple(tuple(m) for m in raw)
                action=np.asarray(apply_word(g,tuple(Move(*m) for m in word)),dtype=np.int32)
                support=np.flatnonzero(action!=identity)
                if len(support)!=3 or not singleton[support].all():raise ValueError('Invalid Flower leaf tool')
                inspect(action,word)
    # A short tool may also disturb a singleton orbit that already has a
    # repair tool. Solve the newly discovered orbit first, then that orbit.
    # Every earlier completed stage remains protected under conjugation.
    # Choose the cheapest valid dependency order, rather than committing to
    # expensive globally isolated tools when a later short repair suffices.
    cycles={};discovery=[];extended=False
    while True:
        peeled={s for i in cycles for s in orbits[i]};added=False
        for p,raw in sorted(leaf_tools.items(),key=lambda r:len(r[1])):
            support={s for s,x in enumerate(p) if s!=x}
            if any(not singleton[s] for s in support):continue
            remaining=support-peeled
            if len(remaining)!=3:continue
            i=owner[min(remaining)]
            if i in cycles or any(owner[s]!=i for s in remaining):continue
            if min(Counter(g.stickers[s].face for s in orbits[i]).values())<2:continue
            first=min(remaining);trip=(first,p[first],p[p[first]])
            if len(set(trip))!=3 or set(trip)!=remaining or p[trip[-1]]!=first:continue
            cycles[i]=raw,trip;discovery.append(i);added=True;break
        if not added and not extended:
            extended=True
            pending=[i for i,o in enumerate(orbits) if i not in cycles and len(o)>2 and all(singleton[s] for s in o)
                     and min(Counter(g.stickers[s].face for s in o).values())>=2]
            if pending:
                for raw_p,aw in tuple(leaf_tools.items()):
                    a=np.asarray(raw_p,dtype=np.int32);ai=np.argsort(a)
                    if not any(any(a[s]!=s for s in orbits[i]) for i in pending):continue
                    for j,(b,bw) in enumerate(atoms):
                        p=invs[j][ai[b[a]]];remaining=set(map(int,np.flatnonzero(p!=identity)))-peeled
                        if len(remaining)!=3 or not any(remaining<=set(orbits[i]) for i in pending):continue
                        word=compact(aw+bw+backwards(aw)+backwards(bw))
                        leaf_tools.setdefault(tuple(map(int,p)),word);added=True
        if not added:break
    leaf_rows=[];allowed={s for i in cycles for s in orbits[i]}
    for i in reversed(discovery):
        raw,trip=cycles[i]
        word=tuple(Move(*m) for m in raw);p=apply_word(g,word)
        support={s for s,x in enumerate(p) if s!=x}
        assert support<=allowed and support&set(orbits[i])==set(trip)
        pieces=tuple(g.stickers[s].piece for s in orbits[i]);base=tuple(g.stickers[s].piece for s in trip)
        t=Transports(cube,pieces,base,both_directions=True)
        while t._expand():pass
        coverage=int(np.count_nonzero(t.parents>=0));assert coverage==len(pieces)*(len(pieces)-1)*(len(pieces)-2)//3
        leaf_rows.append(dict(slots=orbits[i],base=trip,word=raw,coverage=coverage))
        allowed-=set(orbits[i])
    peeled={s for row in leaf_rows for s in row['slots']};core=tuple(s for s in range(degree) if s not in peeled)
    print('LEAF_STAGES',[(len(r['slots']),len(r['word'])) for r in leaf_rows],'CORE',len(core),flush=True)
    if '--probe-cycles' in sys.argv:return
    ids={s:i for i,s in enumerate(core)};pool={}
    for p,w in tuple((tuple(map(int,p)),w) for p,w in atoms)+tuple(small.items()):
        q=tuple(ids[p[s]] for s in core)
        if q!=tuple(range(len(core))) and (q not in pool or len(w)<len(pool[q])):pool[q]=w
    base=sorted(range(len(core)),key=lambda i:(-len(g.pieces[g.stickers[core[i]].piece]),-core[i]))
    certificate=Certificate(len(core),base)
    for p in sorted(pool,key=lambda p:sum(i!=x for i,x in enumerate(p))):certificate.add(p)
    expected=[tuple(r) for r in certificate.trans]
    point_orbits=[];left=set(range(len(core)))
    while left:
        o={min(left)};queue=list(o)
        for beta in queue:
            for p in pool:
                if p[beta] not in o:o.add(p[beta]);queue.append(p[beta])
        point_orbits.append(o);left-=o
    def odd(p,o):
        ids=sorted(o);local={s:i for i,s in enumerate(ids)};values=[local[p[s]] for s in ids]
        return sum(values[i]>x for i in range(len(values)) for x in values[i+1:])%2
    parity=[o for o in point_orbits if len(o)>1 and any(odd(p,o) for p in pool)]
    if butter or master or twins_reference or fourteen:
        # Several tiny orientation orbits have the same parity character.
        # Keep an independent GF(2) column basis, verified on every quotient
        # generator. Their dependent characters cannot distinguish words.
        independent=[];basis={}
        for orbit in parity:
            column=sum(odd(p,orbit)<<j for j,p in enumerate(pool))
            reduced=column
            while reduced:
                pivot=reduced.bit_length()-1
                if pivot not in basis:
                    basis[pivot]=reduced;independent.append(orbit);break
                reduced^=basis[pivot]
        parity=independent
    print('QUOTIENT_ORDER',certificate.order,flush=True)
    rows=(build(pool,base,expected,parity,compact,backwards,preserve_group=True,limit=150,bucket_limit=150,
                report=lambda *r:print(*r,flush=True)) if core else [])
    verified=0
    for level,row in enumerate(rows):
        for beta,record in row.items():
            word=tuple(Move(*m) for m in record['word']);full=apply_word(g,word)
            assert tuple(ids[full[s]] for s in core)==tuple(record['permutation'])
            assert all(full[core[b]]==core[b] for b in base[:level])
            record['permutation']=full;verified+=1
        rows[level]={str(core[int(beta)]):r for beta,r in row.items()}
    data=dict(version=2,geometry=geometry_key(g),source=source_key(),base=[core[b] for b in base],
              core_points=core,leaf_stages=leaf_rows,order=str(certificate.order),transversals=rows,
              verified_transversals=verified,macros=[[(m.axis,m.layer,m.amount) for m in w] for a,w in generators()])
    target=Path('solver/data')/('helicopter_14_jumbling_group.bin' if fourteen else 'twins_pcubes_colour_group.bin' if twins_reference else 'master_clover_colour_group.bin' if master else 'butterflower_colour_group.bin' if butter else 'flower_copter_colour_group.bin' if flower else 'suncube_colour_group.bin' if sun else 'twins_cad_colour_group.bin')
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',target,target.stat().st_size,verified,monotonic()-started,flush=True)


if __name__=='__main__':run('--sun' in sys.argv)
