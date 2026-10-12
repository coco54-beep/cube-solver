"""Compare full entered-state solves with the saved previous centre planner."""
import importlib.util
import json
from pathlib import Path
import sys
import time
import copy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_solvers import make_sample
from solver.solver_n import solve_nxn
import solver.nxn_optimize as planner

def main():
    out=ROOT/'reports/algorithm-upgrades/2026-10-13/nxn-final-certified.jsonl'
    spec=importlib.util.spec_from_file_location('previous_centres',out.parent/'baseline-code/nxn_optimize.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    current=planner.center_atoms
    for n in range(6,18):
        cube,length=make_sample('cube',n,20261013,cover=True)
        row={'order':n,'seed':20261013,'scramble_steps':length}
        initial=dict((p,dict(c.stickers)) for p,c in cube.cubies.items())
        import solver.solver3 as core
        real_core=core.solve_3x3
        captured=[]
        def fixed_core(*args,**kwargs):
            if not captured:captured.append(real_core(*args,**kwargs))
            return copy.deepcopy(captured[0])
        core.solve_3x3=fixed_core
        def previous(cube,positions,cancel,**kwargs):
            word=old.center_atoms(cube,positions,cancel)
            return (word,word) if kwargs.get('return_options') else word
        for label,fn in (('before',previous),('after',current)):
            planner.center_atoms=fn
            started=time.perf_counter();result=solve_nxn(cube)
            seconds=time.perf_counter()-started
            replay=cube.clone();replay.apply_moves(result.moves)
            assert result.success and replay.is_solved(),(n,label,result.message)
            assert initial==dict((p,dict(c.stickers)) for p,c in cube.cubies.items())
            row[label]={'steps':len(result.moves),'seconds':round(seconds,3),'replay':'pass'}
        planner.center_atoms=current
        core.solve_3x3=real_core
        with out.open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
        print(row,flush=True)

if __name__=='__main__':main()
