"""Re-enter regular scrambles as observations, with no move history."""
import sys,json
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.flower_copter import FlowerCopterCube
from cube.flower_copter_aligned import scrambled,observed_colors
from solver.flower_copter import solve

if __name__=='__main__':
    rows=[]
    for length in (30,100,300):
        for seed in range(4):
            started=monotonic();source=scrambled(seed,length)
            entered=FlowerCopterCube(paints=observed_colors(source));before=entered.signature()
            try:
                moves=solve(entered,seconds=15)
                ok=entered.clone().apply_moves(moves).is_solved() and entered.signature()==before
                row=dict(length=length,seed=seed,moves=len(moves),seconds=round(monotonic()-started,3),
                         passed=ok,input_preserved=entered.signature()==before,profile=entered.observation_model)
            except Exception as error:
                row=dict(length=length,seed=seed,passed=False,error=str(error),input_preserved=entered.signature()==before)
            rows.append(row);print(row,flush=True)
    target=Path('reports/expansion/2026-10-29/flower-copter/manual-results.json')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(rows,indent=2),encoding='utf-8')
    if not all(r['passed'] for r in rows):raise SystemExit(1)
