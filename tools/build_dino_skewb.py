"""Build TomZ Dino Skewb three-cycle formulas for both kinds of turn."""
import json
from pathlib import Path
import sys
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import piece_orbits
from solver.polyhedral_reduction import primitives
from solver.lattice_data import geometry_key


def build(kind='dino_skewb'):
    cube=PolyhedralPuzzle(kind,4)
    targets={i:o for i,o in enumerate(piece_orbits(kind,4)) if len(o)>6}
    macros=primitives(cube,targets,use_prepared=False,deep=True)
    data=dict(geometry=geometry_key(cube.geometry),cycles={str(i):dict(
        word=[(m.axis,m.layer,m.amount) for m in word],base=base)
        for i,(word,base) in macros.items()})
    path=Path(__file__).resolve().parents[1]/'solver/data'/f'{kind}_cycles.bin'
    path.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print(kind,{i:len(w) for i,(w,_) in macros.items()},'bytes',path.stat().st_size)


if __name__=='__main__':
    build()
    build('dayan_dino_skewb')
