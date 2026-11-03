"""Broader, time-bounded closed-circuit discovery over legal primitive turns."""
from tools.probe_pisces_circuits import *
from collections import defaultdict

if __name__=='__main__':
    started=time.monotonic();found={};seen={signature(initial)};beam=[(initial,())]
    for depth in range(1,15):
        buckets=defaultdict(list)
        for state,word in beam:
            for a in (range(12) if word else (0,)):
                for x in angles:
                    if word and word[-1]==(a,-x):continue
                    new=step(state,a,x)
                    if new is None:continue
                    k=signature(new)
                    if k in seen:continue
                    seen.add(k);following=word+((a,x),);d=distances(new);score=np.count_nonzero(d>1e-8)
                    if score==0:
                        physical=tuple(Move(axis,0,angle) for axis,angle in following)
                        try:
                            work=PiscesCube().apply_moves(physical);p=work.aligned_permutation()
                        except ValueError:continue
                        if p!=tuple(range(len(p))):
                            found.setdefault(p,physical);print('CLOSED',len(found),following,flush=True)
                    else:buckets[int(score)].append((float(d.sum()),new,following))
        beam=[]
        for score,rows in sorted(buckets.items()):
            rows.sort(key=lambda row:row[0]);beam.extend((s,w) for distance,s,w in rows[:48])
        print('depth',depth,'seen',len(seen),'beam',len(beam),'counts',[(k,len(v)) for k,v in sorted(buckets.items())],'seconds',time.monotonic()-started,flush=True)
        if not beam or time.monotonic()-started>180:break
    out=Path('artifacts/research/pisces');out.mkdir(parents=True,exist_ok=True)
    (out/'raw-actions.json').write_text(json.dumps([dict(permutation=p,word=[[m.axis,m.layer,m.amount] for m in w]) for p,w in found.items()]),encoding='utf-8')
    print('DONE',len(found),flush=True)
