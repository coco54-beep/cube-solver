"""Build state-independent FTO stabilizer assets, without sampled scrambles."""
import json
from pathlib import Path
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cube.polyhedral import PolyhedralPuzzle
from solver.fto import core_points
from solver.lattice_data import geometry_key
from solver.polyhedral import StabilizerChain,simplify


def build():
    records={}
    for order in (2,3,4):
        cube=PolyhedralPuzzle('fto',order)
        points=core_points(cube)
        print('Preparing FTO core',order,'stickers',len(points),flush=True)
        chain=StabilizerChain(cube,points=points)
        rows=[]
        for row in chain.trans:
            entries={}
            for destination,(permutation,word) in row.items():
                moves=simplify(word.flatten(3),3)
                entries[str(destination)]=[list(permutation),[[m.axis,m.layer,m.amount] for m in moves]]
            rows.append(entries)
        records[str(order)]={'geometry':geometry_key(cube.geometry),'points':list(points),'rows':rows}
        print('Prepared',order,'entries',sum(len(row) for row in rows),flush=True)
    path=ROOT/'solver'/'data'/'fto_core.bin'
    path.write_bytes(zlib.compress(json.dumps(records,separators=(',',':')).encode('utf-8'),9))
    print('Saved',path,'bytes',path.stat().st_size,flush=True)


if __name__=='__main__':
    build()
