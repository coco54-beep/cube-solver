"""Finish the current full audit in isolated pytest groups without re-running passes."""
import os,sys,json,re,subprocess,argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/reliability-audit/2026-11-02'


def prepare(jobs):
    nodes=[line.strip() for line in (OUT/'collection.log').read_text(encoding='utf-8',errors='replace').splitlines()
           if line.startswith('tests/')]
    passed=set()
    for log in ('tests.log','tests-core.log'):
        for line in (OUT/log).read_text(encoding='utf-8',errors='replace').splitlines():
            m=re.match(r'^(tests/.*?) PASSED',line)
            if m:passed.add(m[1])
    # This isolated repair run used quiet output; its entire four-file set passed.
    repaired={'test_application_resume.py','test_bandaged_entry.py','test_button_logic_audit.py','test_material_play_pages.py'}
    assert '115 passed' in (OUT/'fixture-regression.log').read_text(encoding='utf-8')
    passed.update(n for n in nodes if Path(n.split('::')[0]).name in repaired)
    counts={}
    for node in nodes:
        if node not in passed:
            file=node.split('::')[0];counts[file]=counts.get(file,0)+1
    groups=[[] for _ in range(jobs)];sizes=[0]*jobs
    for file,count in sorted(counts.items(),key=lambda r:-r[1]):
        i=min(range(jobs),key=sizes.__getitem__);groups[i].append(file);sizes[i]+=count
    data={'collected':len(nodes),'passed_before_groups':len(passed),'passed':sorted(passed),
          'groups':groups,'remaining_counts':sizes}
    (OUT/'regression-plan.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return data


def worker(index):
    os.chdir(ROOT)
    os.environ.update(KIVY_NO_ARGS='1',KIVY_NO_FILELOG='1',KIVY_METRICS_DENSITY='1',KIVY_DPI='96',
                      ANDROID_PRIVATE=str(OUT/f'worker-{index}-private'))
    sys.path.insert(0,str(ROOT))
    from app.desktop_runtime import configure_graphics
    configure_graphics()
    from kivy.config import Config
    Config.set('graphics','window','hidden')
    import pytest
    plan=json.loads((OUT/'regression-plan.json').read_text(encoding='utf-8'))
    passed=set(plan['passed']);result=OUT/f'worker-{index}-results.jsonl'
    result.write_text('',encoding='utf-8')
    class Remaining:
        def pytest_collection_modifyitems(self,config,items):
            keep=[];removed=[]
            for item in items:(removed if item.nodeid in passed else keep).append(item)
            items[:]=keep
            if removed:config.hook.pytest_deselected(items=removed)
        def pytest_runtest_logstart(self,nodeid,location):
            (OUT/f'worker-{index}-current.json').write_text(json.dumps({'nodeid':nodeid}),encoding='utf-8')
        def pytest_runtest_logreport(self,report):
            if report.when=='call' or report.when=='setup' and report.outcome!='passed':
                record={'nodeid':report.nodeid,'outcome':report.outcome,'duration':report.duration,
                        'phase':report.when,'error':str(report.longrepr) if report.failed else None}
                with result.open('a',encoding='utf-8') as stream:stream.write(json.dumps(record,ensure_ascii=False)+'\n')
    code=pytest.main(['-vv','-m','not slow','--maxfail=15','--tb=short','--durations=15',*plan['groups'][index]],plugins=[Remaining()])
    raise SystemExit(code)


def main(jobs):
    plan=prepare(jobs)
    def run(index):
        log=OUT/f'worker-{index}.log'
        with log.open('w',encoding='utf-8') as stream:
            process=subprocess.run([sys.executable,'-u',__file__,'--worker',str(index)],cwd=ROOT,
                                   stdout=stream,stderr=subprocess.STDOUT)
        return {'group':index,'exit_code':process.returncode}
    with ThreadPoolExecutor(max_workers=jobs) as pool:results=list(pool.map(run,range(jobs)))
    records=[]
    for i in range(jobs):
        path=OUT/f'worker-{i}-results.jsonl'
        if path.exists():records.extend(json.loads(line) for line in path.read_text(encoding='utf-8').splitlines())
    summary={'previous_passes':plan['passed_before_groups'],'collected':plan['collected'],
             'new_passes':sum(r['outcome']=='passed' for r in records),
             'skipped':sum(r['outcome']=='skipped' for r in records),
             'failures':[r for r in records if r['outcome']=='failed'],'workers':results}
    (OUT/'regression-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='failures'},ensure_ascii=False),flush=True)
    raise SystemExit(bool(summary['failures']) or any(r['exit_code'] for r in results))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker',type=int);parser.add_argument('--jobs',type=int,default=4)
    args=parser.parse_args()
    if args.worker is not None:worker(args.worker)
    else:main(args.jobs)
