"""Prepare independent FTO orbit cycles from exact move permutations."""
import json
from pathlib import Path
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import piece_orbits
from solver.polyhedral_reduction import primitives
from solver.lattice_data import geometry_key


def build():
    records={}
    for order in (3,4):
        cube=PolyhedralPuzzle('fto',order)
        g=cube.geometry
        targets={i:orbit for i,orbit in enumerate(piece_orbits('fto',order))
                 if len(orbit)>6 and len(g.pieces[orbit[0]])<3}
        print('Preparing FTO cycles',order,'orbits',list(targets),flush=True)
        cycles=primitives(cube,targets,use_prepared=False)
        records[str(order)]={'geometry':geometry_key(g),
                            'cycles':{str(i):{'word':[[m.axis,m.layer,m.amount] for m in word],
                                              'base':list(base)} for i,(word,base) in cycles.items()}}
        print('Prepared',order,'move counts',
              {i:len(word) for i,(word,_) in cycles.items()},flush=True)
    path=ROOT/'solver'/'data'/'fto_cycles.bin'
    path.write_bytes(zlib.compress(json.dumps(records,separators=(',',':')).encode('utf-8'),9))
    print('Saved',path,'bytes',path.stat().st_size,flush=True)


if __name__=='__main__':
    build()
