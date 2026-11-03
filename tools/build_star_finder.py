"""Discover original staged cycles on Star Finder's actual panel actions."""
import json
from pathlib import Path
import sys
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle,Move
from solver.polyhedral import piece_orbits,apply_word
from solver.polyhedral_reduction import Transports
from solver.lattice_data import geometry_key
from tools.build_rex_cycles import discover,flip_pair


def run():
    kind='kairis_star_finder';cube=PolyhedralPuzzle(kind,3);g=cube.geometry
    data=discover(kind);orbits=piece_orbits(kind,3);coverage={}
    for i in data['order']:
        orbit=orbits[i];base=tuple(data['cycles'][str(i)]['base'])
        transport=Transports(cube,orbit,base,both_directions=True)
        while transport._expand():pass
        count=int((transport.parents>=0).sum());expected=len(orbit)*(len(orbit)-1)*(len(orbit)-2)//3
        if count!=expected:raise ValueError('Star Finder lacks full triple coverage')
        coverage[str(i)]=count;print('verified',i,count,flush=True)
    edge=next(i for i,o in enumerate(orbits) if len(o)==30)
    word=tuple(Move(*m) for m in data['cycles'][str(edge)]['word'])
    data.update(version=1,geometry=geometry_key(g),coverage=coverage,edge_orbit=edge,
                edge_flip=flip_pair(cube,orbits[edge],word))
    path=Path('solver/data/kairis_star_finder_cycles.bin')
    path.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',path,path.stat().st_size,flush=True)


if __name__=='__main__':run()
