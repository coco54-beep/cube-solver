"""Isolate difficult entry/solve/replay cases; report time limits honestly.

Each case gets its own process, empty solution caches and visible-only input.
A parent deadline also covers input matching and solvers that ignore cancel.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'


def worker(kind,seed,turns,budget,folder):
    from tools.audit_random_input_matrix import run
    from solver import solution_loops
    from solver import polyhedral_reduction
    original=solution_loops.shorten_polyhedral_word
    measurements=[]
    def measured(cube,word,cancel=None):
        word=tuple(word);started=monotonic()
        result=original(cube,word,cancel)
        measurements.append({'before':len(word),'after':len(result),
                             'seconds':round(monotonic()-started,3)})
        return result
    stages=[];original_stage=polyhedral_reduction.color_orbit_word
    def measured_stage(cube,transports,orbit,primitive,fallback,*args,**kwargs):
        result=original_stage(cube,transports,orbit,primitive,fallback,*args,**kwargs)
        stages.append({'pieces':len(orbit),'before':len(fallback),'after':len(result)})
        return result
    polyhedral_reduction.color_orbit_word=measured_stage
    solution_loops.shorten_polyhedral_word=measured
    row=run(kind,seed,turns,folder,budget)
    row['shortening']=measurements
    row['colour_stage_plans']=stages
    path=folder/'cases'/f'{kind}-{seed}-{turns}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    return row


def isolated(kind,seed,turns,budget,folder,grace):
    row={'kind':kind,'seed':seed,'scramble_turns':turns}
    tag=f'{kind}-{seed}-{turns}';path=folder/'cases'/f'{tag}.json'
    cmd=[sys.executable,str(Path(__file__).resolve()),'--worker','--kind',kind,
         '--seed',str(seed),'--turns',str(turns),'--budget',str(budget),'--out',str(folder)]
    started=monotonic()
    try:
        result=subprocess.run(cmd,cwd=ROOT,capture_output=True,encoding='utf-8',
                              errors='replace',timeout=budget+grace)
        log=result.stdout+result.stderr
        if result.returncode==0 and path.exists():
            row=json.loads(path.read_text(encoding='utf-8'))
        else:row.update(success=False,worker_exit=result.returncode,error='worker did not produce a successful report')
    except subprocess.TimeoutExpired as exc:
        def text(value):return value.decode('utf-8','replace') if isinstance(value,bytes) else value or ''
        log=text(exc.stdout)+text(exc.stderr)
        row.update(success=False,evaluation_budget_hit=True,hard_timeout=True,
                   seconds=round(monotonic()-started,3))
    folder.joinpath('logs').mkdir(parents=True,exist_ok=True)
    (folder/'logs'/f'{tag}.log').write_text(log,encoding='utf-8')
    row['process_seconds']=round(monotonic()-started,3)
    return row


def main():
    from tools.audit_random_input_matrix import SUPPORTED,ADDITIONAL
    parser=argparse.ArgumentParser()
    parser.add_argument('--kind',action='append',choices=SUPPORTED)
    parser.add_argument('--seed',action='append',type=int)
    parser.add_argument('--turns',action='append',type=int)
    parser.add_argument('--all',action='store_true')
    parser.add_argument('--additional',action='store_true',help='newly added visible-input adapters only')
    parser.add_argument('--retry-from',action='append',type=Path,
                        help='rerun only unresolved cases from an earlier results.json')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--jobs',type=int,default=2)
    parser.add_argument('--budget',type=float,default=20.)
    parser.add_argument('--grace',type=float,default=45.)
    parser.add_argument('--out',type=Path,default=ROOT/'reports/optimization/2026-10-26/deep-inputs')
    args=parser.parse_args()
    turns=args.turns or [30,100];seeds=args.seed or [20261104,20261105]
    if args.jobs<1 or args.budget<=0 or args.grace<=0 or min(turns)<1:parser.error('positive limits required')
    folder=args.out.resolve();folder.mkdir(parents=True,exist_ok=True)
    kinds=SUPPORTED if args.all else ADDITIONAL if args.additional else args.kind or ['mixup_plus_344','tangram_extreme','master_brilic']
    if args.worker:
        worker(kinds[0],seeds[0],turns[0],args.budget,folder);return
    cases=[(kind,seed,n) for n in turns for kind in kinds for seed in seeds]
    if args.retry_from:
        cases=list(dict.fromkeys((r['kind'],r['seed'],r['scramble_turns'])
                   for path in args.retry_from for r in json.loads(path.read_text(encoding='utf-8'))
                   if not r.get('replay_solved')))
    rows=[]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures=[pool.submit(isolated,kind,seed,n,args.budget,folder,args.grace)
                 for kind,seed,n in cases]
        for future in as_completed(futures):
            row=future.result();rows.append(row)
            (folder/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(row,ensure_ascii=False),flush=True)
    summary={'cases':len(rows),'solved_and_replayed':sum(bool(r.get('replay_solved')) for r in rows),
             'evaluation_budget_hits':sum(bool(r.get('evaluation_budget_hit')) for r in rows),
             'other_failures':sum(not r.get('replay_solved') and not r.get('evaluation_budget_hit') for r in rows)}
    (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    if summary['solved_and_replayed']!=summary['cases']:raise SystemExit(1)


if __name__=='__main__':main()
