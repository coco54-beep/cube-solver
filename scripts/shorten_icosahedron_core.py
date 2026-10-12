"""Produce optional shorter core words without editing the shared base asset."""
from collections import deque
from pathlib import Path
import json
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cube.polyhedral import PolyhedralPuzzle,Move
from solver.icosahedron import core_points
from solver.polyhedral import simplify
from solver.polyhedral_optimize import _atoms

def main():
    source=ROOT/'solver/data/icosahedron_core.bin'
    data=json.loads(zlib.decompress(source.read_bytes()))
    output={};report=[]
    for n in range(2,6):
        cube=PolyhedralPuzzle('icosahedron',n);points=core_points(cube)
        ids={s:i for i,s in enumerate(points)}
        def action(move):
            p=cube.geometry.permutation(move)
            return bytes(ids[p[s]] for s in points)
        identity=bytes(range(len(points)))
        atoms={action(m):m for m in _atoms(cube)};atoms.pop(identity,None)
        rules={identity:()};queue=deque([identity])
        while queue and len(rules)<80000:
            state=queue.popleft();word=rules[state]
            if len(word)==3:continue
            for p,m in atoms.items():
                nxt=bytes(map(p.__getitem__,state))
                if nxt not in rules:
                    rules[nxt]=word+(m,);queue.append(nxt)
        def effect(word):
            state=identity
            for m in word:state=bytes(map(action(m).__getitem__,state))
            return state
        rows=[]
        for prime,relations in data[str(n)]['relations'].items():
            for index,relation in enumerate(relations):
                original=tuple(Move(*m) for m in relation['word'])
                result=list(simplify(original,5));i=0
                while i<len(result):
                    state=identity;best=None
                    for stop in range(i,min(len(result),i+18)):
                        state=bytes(map(action(result[stop]).__getitem__,state))
                        replacement=rules.get(state)
                        if replacement is not None and len(replacement)<stop-i+1:
                            gain=stop-i+1-len(replacement)
                            if best is None or gain>best[0]:best=(gain,stop+1,replacement)
                    if best is None:i+=1
                    else:
                        _,stop,replacement=best
                        result[i:stop]=replacement;i=max(0,i-17)
                result=simplify(result,5)
                assert effect(result)==effect(original)
                if len(result)<len(original):
                    rows.append({'prime':prime,'index':index,'original':relation['word'],
                                 'word':[[m.axis,m.layer,m.amount] for m in result]})
                report.append({'order':n,'prime':prime,'index':index,
                               'before':len(original),'after':len(result),'core_action':'identical'})
        output[str(n)]={'geometry':data[str(n)]['geometry'],'replacements':rows}
        print(n,len(rules),len(rows),'shortened words',flush=True)
    if any(v['replacements'] for v in output.values()):
        target=ROOT/'solver/data/icosahedron_short_core.bin'
        tmp=target.with_suffix('.tmp');tmp.write_bytes(zlib.compress(json.dumps(output).encode(),9));tmp.replace(target)
    (ROOT/'reports/algorithm-upgrades/2026-10-13/icosahedron-words.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
