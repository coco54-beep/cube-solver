"""Bundle independent orbit cycles for the Icosamate family."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import piece_orbits
from solver.polyhedral_reduction import primitives
from solver.lattice_data import geometry_key


def build():
    records={}
    for order in (2,3,4,5):
        cube=PolyhedralPuzzle('icosahedron',order)
        g=cube.geometry
        targets={i:orbit for i,orbit in enumerate(piece_orbits('icosahedron',order))
                 if len(orbit)==60}
        print('Preparing Icosamate',order,'with',len(targets),'orbits',flush=True)
        cycles=primitives(cube,targets,progress=lambda done,total:
                          print('Cycles',order,done,total,flush=True) if done%1024==0 else None)
        records[str(order)]={'geometry':geometry_key(g),
                            'cycles':{str(i):{'word':[[m.axis,m.layer,m.amount] for m in word],
                                              'base':list(base)} for i,(word,base) in cycles.items()}}
        path=ROOT/'solver'/'data'/'icosahedron_cycles.json'
        path.write_text(json.dumps(records,separators=(',',':'))+'\n',encoding='utf-8')
        print('Saved',order,path,flush=True)


if __name__=='__main__':
    build()
