"""Replay every expanded lesson and optionally state-solve its full example."""
import argparse,json,os,sys,time,threading,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('KIVY_NO_ARGS','1')
from candidate_puzzles import REQUESTED
from demo.solutions import make_scrambled_demo,build_example,verified_solution_lessons,state_signature
from demo.expanded_tutorials import lessons,tutorial
from demo.expanded_curriculum import chapters


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--solve',action='store_true')
    parser.add_argument('--timeout',type=float,default=60.)
    parser.add_argument('--only',nargs='*')
    parser.add_argument('--output',default='reports/demo-audit/2026-10-24/expanded-teaching.json')
    args=parser.parse_args();rows=[];target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    for entry in REQUESTED:
        if args.only and entry.kind not in args.only:continue
        started=time.monotonic();row={'kind':entry.kind,'order':entry.n};timer=None
        try:
            mode=(entry.kind,entry.n);count=0
            for step in lessons(*mode):
                for case in step['cases']:
                    work=build_example(mode,case)
                    for move in case['moves']:work.apply_move(move)
                    if not work.is_solved():raise AssertionError('Local example failed')
                    count+=1
            row['examples']=count
            row['original_chapters']=len(chapters(entry.kind))
            row['external_links']=False
            if args.solve:
                from services.solve_service import SolveService,CancelToken
                initial=make_scrambled_demo(mode);before=state_signature(initial);work=initial.clone()
                if hasattr(work,'history'):work.history=None
                cancel=CancelToken();answers=[];timer=threading.Timer(args.timeout,cancel.cancel);timer.daemon=True;timer.start()
                SolveService()._run(work,answers.append,None,cancel)
                if len(answers)!=1:raise AssertionError('Missing solver result')
                full=verified_solution_lessons(initial,answers[0])
                assert state_signature(initial)==before
                row['complete_moves']=len(full[0]['cases'][0]['moves']);row['history_removed']=True
                row['verified_sections']=len(full)-1
            row['status']='pass'
        except Exception:row.update(status='fail',error=traceback.format_exc())
        finally:
            if timer:timer.cancel()
        row['seconds']=round(time.monotonic()-started,3);rows.append(row)
        target.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in row.items() if k!='references'},ensure_ascii=True),flush=True)
    return 0 if rows and all(r['status']=='pass' for r in rows) else 1


if __name__=='__main__':raise SystemExit(main())
