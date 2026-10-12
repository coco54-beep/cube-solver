"""Compare compaction against the exact word generated in the same solve."""
from pathlib import Path
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.audit_solvers import make_sample
import solver.polyhedral as module

def main():
    cases=[('fto',3),('fto',4),('skewb',5),('skewb',7),('pyraminx',4),('pyraminx',5),('pyraminx',7),
           ('moyu',4),('moyu',5),('moyu',7),('war_drum',4),('war_drum',5),('blossom',3),
           ('dino',4),('dino',6),('clover',3),('eight_petals',3),('megaminx',2),('megaminx',3)]
    path=ROOT/'reports/algorithm-upgrades/2026-10-13/compaction.jsonl'
    raw=module._solve_and_optimize
    with path.open('w',encoding='utf-8') as stream:
        for kind,n in cases:
            cube,_=make_sample(kind,n,20261013,cover=True);initial=tuple(cube.colors)
            baselines=[]
            def capture(*args,**kwargs):
                word=raw(*args,**kwargs);baselines.append(word);return word
            module._solve_and_optimize=capture
            started=time.perf_counter();word=module.solve_polyhedral(cube)
            module._solve_and_optimize=raw
            replay=cube.entered()
            for move in word:replay.apply_move(move)
            assert replay.is_solved() and initial==tuple(cube.colors)
            assert len(word)<=len(baselines[0])
            row={'kind':kind,'order':n,'seed':20261013,'before':len(baselines[0]),'after':len(word),
                 'seconds':round(time.perf_counter()-started,3),'replay':'pass'}
            stream.write(json.dumps(row)+'\n');stream.flush();print(row,flush=True)

if __name__=='__main__':main()
