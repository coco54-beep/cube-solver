"""Author fixed full courses by independent state solves; never invert scramble history."""
import os,sys,json,zlib,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('KIVY_NO_ARGS','1')
from candidate_puzzles import REQUESTED
from demo.solutions import make_scrambled_demo
from demo.course import record
from services.solve_service import SolveService,CancelToken


def main():
    target=Path('demo/data/expanded_courses.bin');models={};rows=[]
    selected=set(sys.argv[1:])
    if selected and target.exists():models=json.loads(zlib.decompress(target.read_bytes()))['models']
    folder=Path('reports/course-audit/2026-10-25');folder.mkdir(parents=True,exist_ok=True)
    for entry in REQUESTED:
        if selected and entry.kind not in selected:continue
        initial=make_scrambled_demo((entry.kind,entry.n))
        if hasattr(initial,'history'):initial.history=None
        answers=[];cancel=CancelToken();timer=threading.Timer(90,cancel.cancel);timer.daemon=True;timer.start()
        try:
            SolveService()._run(initial.clone(),answers.append,None,cancel)
            assert len(answers)==1 and answers[0].success,(entry.kind,answers)
            models[entry.kind]=record(initial,answers[0])
            row=dict(kind=entry.kind,moves=len(answers[0].moves),sections=len(models[entry.kind]['sections']),status='pass')
            rows.append(row);print(json.dumps(row),flush=True)
            (folder/'courses.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        finally:timer.cancel()
    target.write_bytes(zlib.compress(json.dumps(dict(version=1,models=models),ensure_ascii=False,separators=(',',':')).encode(),9))
    print(dict(courses=len(models),bytes=target.stat().st_size))


if __name__=='__main__':main()
