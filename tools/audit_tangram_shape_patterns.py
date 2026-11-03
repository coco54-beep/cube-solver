"""Independently prove exact abstract distances and coupled-skin relations."""
import sys
import json
import hashlib
from pathlib import Path
from collections import deque
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from solver.tangram_geometry import geometry
from solver.tangram_shapes import patterns,shape_fingerprint
from tools.build_tangram_shape_patterns import projected_states


def run():
    model=geometry('tangram_extreme');table=patterns();caps,tc=projected_states(model,table.cap_mask)
    assert {state:i for i,state in enumerate(caps)}==table.caps
    parts=[projected_states(model,4095<<(4+12*i)) for i in range(6)]
    n=924;nn=n*n;report=dict(shape_model=shape_fingerprint(),distances=[],relations=[])
    for a,b,payload in table.distances:
        values=np.frombuffer(payload,dtype=np.uint8);ta=parts[a][1];tb=parts[b][1];edges=0
        assert values[0]==0 and np.count_nonzero(values==0)==1 and np.all(values!=255)
        for start in range(0,len(values),200000):
            indices=np.arange(start,min(start+200000,len(values)),dtype=np.int32)
            c=indices//nn;x=indices//n%n;y=indices%n
            lowered=values[indices]==0
            for i in range(len(model.moves)):
                cc=tc[i,c];xx=ta[i,x];yy=tb[i,y];valid=(cc>=0)&(xx>=0)&(yy>=0)
                dest=cc[valid]*nn+xx[valid]*n+yy[valid]
                delta=values[dest].astype(np.int16)-values[indices[valid]].astype(np.int16)
                assert np.all(np.abs(delta)<=1)
                lowered[valid]|=delta==-1;edges+=len(dest)
            assert np.all(lowered)
        report['distances'].append(dict(pair=[a,b],states=len(values),diameter=int(values.max()),verified_directed_edges=edges))
    for a,b,expected in table.relations:
        ta=parts[a][1];tb=parts[b][1];pending=deque([0]);seen={0};edges=0
        assert expected[0]==0
        while pending:
            state=pending.popleft();c,x=divmod(state,n);y=expected[state]
            for i in range(len(model.moves)):
                cc,xx,yy=tc[i,c],ta[i,x],tb[i,y]
                if min(cc,xx,yy)<0:continue
                dest=int(cc*n+xx);assert expected[dest]==yy;edges+=1
                if dest not in seen:seen.add(dest);pending.append(dest)
        assert len(seen)==len(caps)*n
        report['relations'].append(dict(pair=[a,b],states=len(seen),verified_directed_edges=edges))
    path=Path('solver/data/tangram_extreme_shape_patterns.bin')
    report.update(asset=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    out=Path('reports/solver-audit/2026-10-23/tangram-shape-pattern-proof.json')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':run()
