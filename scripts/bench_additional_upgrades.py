"""Measure additional candidates against the baseline from the same call."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.audit_solvers import make_sample

def main():
    out=ROOT/'reports/algorithm-upgrades/2026-10-13/additional.jsonl'
    cases=[(k,3) for k in ('axis','windmill','fisher','mirror_tower','square1')]
    cases += [('cube',5)]+[(k,n) for k in ('mastermorphix','mirror') for n in range(4,10)]
    with out.open('w',encoding='utf-8') as stream:
        for kind,n in cases:
            for seed in (54,13):
                cube,_=make_sample(kind,n,seed)
                baseline=[]
                if kind in ('axis','windmill','fisher'):
                    import solver.shape_cube as mod
                    name='_solve_shape_cube';entry=mod.solve_shape_cube
                elif kind=='cube':
                    import solver.solver5 as mod
                    name='_solve_5x5';entry=mod.solve_5x5
                elif kind in ('mastermorphix','mirror'):
                    import solver.solver_n as mod
                    name='_solve_nxn';entry=mod.solve_nxn
                else:
                    if kind=='square1':
                        from solver.square1 import solve_square1 as entry
                    else:
                        from solver.mirror_tower_optimal import solve_mirror_tower as entry
                    old=entry(cube,optimize_budget=0);baseline=[old]
                    name=None
                if name:
                    raw=getattr(mod,name)
                    def capture(*args,**kwargs):
                        value=raw(*args,**kwargs)
                        if not baseline:baseline.append(value)
                        return value
                    setattr(mod,name,capture)
                started=time.perf_counter();result=entry(cube);seconds=time.perf_counter()-started
                if name:setattr(mod,name,raw)
                word=result.moves if hasattr(result,'success') else result
                old=baseline[0].moves if hasattr(baseline[0],'success') else baseline[0]
                assert not hasattr(result,'success') or result.success,(kind,n,result.message)
                assert len(word)<=len(old),(kind,n)
                replay=cube.clone()
                for move in word:replay.apply_move(move)
                assert replay.is_solved(),(kind,n)
                row={'kind':kind,'order':n,'seed':seed,'before':len(old),'after':len(word),
                     'seconds':round(seconds,3),'replay':'pass'}
                stream.write(json.dumps(row)+'\n');stream.flush();print(row,flush=True)

if __name__=='__main__':main()
