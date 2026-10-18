"""Desktop process-RSS audit; run each puzzle in an isolated subprocess."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import psutil  # Development tool only; not an application dependency.


CASES=(('megaminx',13),('football',5),('icosahedron',5),('pyraminx',7),
       ('moyu',5),('skewb',7),('dino',6),('fto',4),('war_drum',5),('pentahedron',5))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('tmp/solver-memory-audit-1.2.29.json'))
    parser.add_argument('--timeout',type=float,default=180)
    parser.add_argument('--standard',action='store_true',help='Check ordinary 3/4/5/6/17 instead of polyhedra')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    rows=[]
    cases=tuple(('cube',n) for n in (3,4,5,6,17)) if args.standard else CASES
    for kind,n in cases:
        print('Checking',kind,n,flush=True)
        command=([sys.executable,'-m','tools.bench_standard_memory',str(n)] if kind=='cube' else
                 [sys.executable,'-m','tools.bench_polyhedral',kind,str(n),'12345'])
        process=subprocess.Popen(command,
                                 cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        monitor=psutil.Process(process.pid)
        peak=0; start=time.monotonic(); timed_out=False
        while process.poll() is None:
            try: peak=max(peak,monitor.memory_info().rss)
            except psutil.NoSuchProcess: pass
            if time.monotonic()-start>args.timeout:
                timed_out=True; process.kill(); break
            time.sleep(.05)
        stdout,stderr=process.communicate()
        row={'kind':kind,'n':n,'process_peak_rss_mib':round(peak/1024**2,2)}
        if timed_out: row['status']='timeout'
        elif process.returncode:
            row.update(status='error',error=stderr.decode('utf-8','replace')[-4000:])
        else:
            # Some reference solvers print table-loading messages first.
            row.update(json.loads(stdout.decode('utf-8','replace').splitlines()[-1]))
            row['status']='passed' if row['replay_ok'] else 'failed'
        rows.append(row)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        print(row['status'],row['process_peak_rss_mib'],'MiB',flush=True)


if __name__=='__main__':main()
