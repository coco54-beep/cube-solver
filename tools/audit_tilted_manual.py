"""Re-enter independent raw-turn observations; never supply a move history.

The Clover prototype is development-only and not a physical-model approval.
Colour-circuit scrambles and raw walks are different test distributions.
"""
import argparse,importlib,json,os,sys,time
from pathlib import Path
from random import Random
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from cube.pisces import PiscesCube
from cube.hexagram import HexagramCube
from cube.clover_pyraminx import CloverPyraminxCube
from services.failures import classify


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=10.)
    parser.add_argument('--seeds',type=int,default=4)
    parser.add_argument('--out',type=Path,default=Path('reports/expansion/2026-10-29/raw-manual'))
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True);rows=[]
    for module,factory in (('pisces',PiscesCube),('hexagram',HexagramCube),('clover_pyraminx',CloverPyraminxCube)):
        solve=importlib.import_module('solver.'+module).solve
        for length in (30,100):
            for seed in range(args.seeds):
                rng=Random(seed);source=factory();previous=-1
                for _ in range(length):
                    choices=list(source.moves());rng.shuffle(choices)
                    # A jumble can temporarily block every other axis. Prefer
                    # another axis but allow the last cap to turn back out.
                    choices.sort(key=lambda m:m.axis==previous)
                    for m in choices:
                        if source.can_apply(m):source.apply_move(m);previous=m.axis;break
                    else:raise AssertionError('No legal next axis')
                observation=json.loads(json.dumps(source.observation_data()))
                entered=factory.from_observation(observation);before=entered.signature();started=time.monotonic()
                row=dict(model=module,length=length,seed=seed,budget=args.seconds,research_only=module=='clover_pyraminx')
                try:
                    word=solve(entered,seconds=args.seconds)
                    assert entered.clone().apply_moves(word).is_solved()
                    row.update(status='solved',moves=len(word))
                except (TimeoutError,ValueError) as error:
                    row.update(status=classify(exception=error),error=str(error))
                    state_file=args.out/f'{module}-{length}-{seed}.json'
                    state_file.write_text(json.dumps(observation,separators=(',',':')),encoding='utf-8')
                    row['observation']=state_file.name
                assert entered.signature()==before
                row.update(seconds=round(time.monotonic()-started,3),input_preserved=True);rows.append(row)
                (args.out/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
                print(json.dumps(row),flush=True)


if __name__=='__main__':main()
