"""Replay every complete demo from an independently seeded scramble."""
import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('KIVY_NO_ARGS','1')
from demo.solutions import make_scrambled_demo,verified_solution_lessons,state_signature
from services.solve_service import SolveService,CancelToken
from ui.screens.irregular_directory_screen import IMPLEMENTED_ORDERS,SPECIAL_PUZZLES


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='reports/demo-audit/2026-10-12/complete-solutions.jsonl')
    parser.add_argument('--timeout',type=float,default=120)
    parser.add_argument('--only',nargs='*')
    args=parser.parse_args()
    modes=[2,3,4,5]+[(k,n) for k,ns in IMPLEMENTED_ORDERS.items() for n in ns if n<=5]
    modes += [(k,3) for k in SPECIAL_PUZZLES if k not in IMPLEMENTED_ORDERS]
    if args.only:
        modes=[m for m in modes if (f'{m[0]}:{m[1]}' if isinstance(m,tuple) else str(m)) in args.only]
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    failures=0
    with target.open('w',encoding='utf8') as stream:
        for mode in modes:
            started=time.perf_counter()
            cancel=CancelToken()
            timer=threading.Timer(args.timeout,cancel.cancel)
            timer.daemon=True
            answers=[]
            row={'mode':mode,'seed':54}
            try:
                initial=make_scrambled_demo(mode,seed=54)
                signature=state_signature(initial)
                timer.start()
                SolveService()._run(initial.clone(),answers.append,None,cancel)
                if len(answers)!=1:raise ValueError('No solver result')
                result=answers[0]
                lessons=verified_solution_lessons(initial,result)
                if state_signature(initial)!=signature:raise ValueError('Starting state was mutated')
                row.update(status='pass',moves=len(lessons[0]['cases'][0]['moves']),phases=len(lessons)-1)
            except Exception as exc:
                row.update(status='fail',error=str(exc))
                failures+=1
            finally:
                timer.cancel()
            row['seconds']=round(time.perf_counter()-started,3)
            stream.write(json.dumps(row,ensure_ascii=False)+'\n');stream.flush()
            print(json.dumps(row,ensure_ascii=True),flush=True)
    print(f'{len(modes)} modes; {failures} failures; report: {target}',flush=True)
    return bool(failures)


if __name__=='__main__':
    raise SystemExit(main())
