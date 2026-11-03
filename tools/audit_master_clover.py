"""Re-enter closed double-layer observations on a fresh blank shell."""
import sys,json
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.master_clover import MasterCloverCube
from cube.master_clover_aligned import scrambled,observed_colors
from solver.master_clover import solve


def run():
    rows=[]
    for length in (30,100,300):
        for seed in range(8):
            source=scrambled(seed,length);paints=observed_colors(source)
            entered=MasterCloverCube(paints=(-1,)*120)
            for face in range(6):
                for i,(h,f,p) in enumerate(entered.panels):
                    if f==face:entered.paint(i,paints[i])
            before=entered.signature();start=perf_counter();word=solve(entered,seconds=15);seconds=perf_counter()-start
            assert entered.signature()==before and entered.clone().apply_moves(word).is_solved()
            rows.append(dict(seed=seed,length=length,passed=True,moves=len(word),seconds=round(seconds,4),input_unchanged=True))
            print(length,seed,len(word),round(seconds,3),flush=True)
    target=Path(__file__).resolve().parents[1]/'reports/expansion/2026-10-29/master-clover/manual-results.json'
    target.write_text(json.dumps(rows,indent=2),encoding='utf8')


if __name__=='__main__':run()
