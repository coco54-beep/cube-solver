"""Summarize finished test reports and exact production asset hashes."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-23'


def run():
    reports=(f'reports/solver-audit/{DAY}/state-reduction-final-tests.xml',
             f'reports/solver-audit/{DAY}/camouflage-deep-final-tests.xml',
             f'reports/input-audit/{DAY}/actual-manual-controls-final.xml',
             f'reports/input-audit/{DAY}/pentacle-manual-service-final.xml',
             f'reports/solver-audit/{DAY}/existing-state-solvers-regression.xml')
    suites=[];unique=set()
    for filename in reports:
        path=ROOT/filename;root=ET.fromstring(path.read_bytes());cases=list(root.iter('testcase'))
        failed=[c for c in cases if c.find('failure') is not None or c.find('error') is not None]
        skipped=[c for c in cases if c.find('skipped') is not None]
        if not cases or failed or skipped:raise ValueError(('Acceptance is incomplete',filename))
        unique.update((c.get('classname'),c.get('name')) for c in cases)
        suites.append(dict(report=filename,passed=len(cases),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    assets={}
    names=('ai_shapes','ai_group','burr_shapes','burr_group','cuboid_442_orientations',
           'cuboid_442_group','pentacle_group','mixup_plus_333_group','mixup_plus_334_group','mixup_plus_344_group')
    for name in names:
        path=ROOT/'solver/data'/(name+'.bin');raw=path.read_bytes()
        row=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        if name.endswith('_group'):
            data=json.loads(zlib.decompress(raw))
            for key in ('order','verified_transversals','exhaustive_layouts','verified_edges','parity_bound','weighted_transversals'):
                if key in data:row[key]=data[key]
        assets[path.name]=row
    folder=ROOT/f'reports/input-audit/{DAY}/mixup-fresh-probes'
    mixup=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('*.json')) if not p.name.endswith('-observations.json')]
    assert len(mixup)==8 and all(r['success'] and r['history_empty'] and r['replay_solved'] for r in mixup)
    result=dict(date=DAY,method='Visible-only reentry into blank models, empty history, state solve and independent legal replay.',
                unique_test_cases=len(unique),test_suites=suites,production_assets=assets,mixup_saved_visible_inputs=mixup,
                remaining_limits=['Camouflage uses a bounded 45-second search, not a complete constructive solver.',
                                  'Mixup and Tangram Extreme shape restoration still has search limits.',
                                  'Colour-coset matching has explicit node/time/cancellation limits.',
                                  'Solutions can be long. No APK or Windows release build or physical phone test was performed.'])
    target=ROOT/f'reports/solver-audit/{DAY}/manual-state-acceptance.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(unique_test_cases=len(unique),suites=[s['passed'] for s in suites],mixup_inputs=len(mixup))))


if __name__=='__main__':run()
