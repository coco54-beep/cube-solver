"""Prepare the Lattice solver's state-independent cycle assets."""
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
    for order in (4,6):
        cube=PolyhedralPuzzle('dino',order)
        targets={i:orbit for i,orbit in enumerate(piece_orbits('dino',order)) if len(orbit)>6}
        print('Preparing Lattice',order,'with',len(targets),'orbits',flush=True)
        cycles=primitives(cube,targets,use_prepared=False,deep=True)
        records[str(order)]={'geometry':geometry_key(cube.geometry),
                            'cycles':{str(i):{'word':[[m.axis,m.layer,m.amount] for m in word],
                                              'base':list(base)} for i,(word,base) in cycles.items()}}
    path=ROOT/'solver'/'data'/'lattice_cycles.json'
    path.write_text(json.dumps(records,separators=(',',':'))+'\n',encoding='utf-8')
    print('Saved',path,flush=True)


if __name__=='__main__':
    build()
