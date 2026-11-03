"""Summarize the current no-quota regressions without double counting tests."""
import hashlib
import json
from pathlib import Path
from statistics import median
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'reports/solver-audit/2026-10-23'


def run():
    files=('search-recovery-final-tests.xml','finite-group-no-quota-tests.xml',
           'remaining-families-final-regression.xml','search-policy-compatibility-tests.xml')
    unique=set();reports=[];shape_times=[];shape_moves=[]
    for name in files:
        path=FOLDER/name;root=ET.fromstring(path.read_bytes());cases=list(root.iter('testcase'))
        if not cases or any(c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None for c in cases):
            raise ValueError(('Acceptance is incomplete',name))
        unique.update((c.get('classname'),c.get('name')) for c in cases)
        reports.append(dict(file=name,passed=len(cases),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if name==files[0]:
            for case in cases:
                if not case.get('name','').startswith('test_thousand_turn_shape_recovery'):continue
                properties={p.get('name'):p.get('value') for p in case.iter('property')}
                shape_times.append(float(properties['shape_seconds']));shape_moves.append(int(properties['shape_moves']))
    proof=json.loads((FOLDER/'tangram-completeness-proof.json').read_text())
    pattern_proof=json.loads((FOLDER/'tangram-shape-pattern-proof.json').read_text())
    assert len(shape_times)==24 and len(proof)==2
    assert pattern_proof['sha256']==hashlib.sha256((ROOT/'solver/data/tangram_extreme_shape_patterns.bin').read_bytes()).hexdigest()
    assets={}
    for name in ('complete_search.py','tangram_shapes.py','tangram_table.py','mixup_complete.py','cuboid_search.py'):
        assets['solver/'+name]=hashlib.sha256((ROOT/'solver'/name).read_bytes()).hexdigest()
    data=dict(date='2026-10-23',unique_passed_tests=len(unique),reports=reports,
              tangram_model_completeness=proof,exact_pattern_distance_edges=sum(r['verified_directed_edges'] for r in pattern_proof['distances']),
              thousand_turn_shape_recovery=dict(cases=24,min_seconds=min(shape_times),median_seconds=median(shape_times),max_seconds=max(shape_times),
                                                min_moves=min(shape_moves),max_moves=max(shape_moves)),
              source_hashes=assets,
              limits=['Completeness refers to the current finite physical model.',
                      'Mixup/Camouflage recovery is complete search, not a guaranteed fast constructive solver.',
                      'Deep saved inputs passed through fast reductions; physical fallback performance was tested mainly on shallow entries.',
                      'No phone performance test or release package build was performed.'])
    (FOLDER/'search-limit-removal-acceptance.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=len(unique),suites=[r['passed'] for r in reports],shape_recovery=data['thousand_turn_shape_recovery'])))


if __name__=='__main__':run()
