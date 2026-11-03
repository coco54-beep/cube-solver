"""Prepare isolated three-cycles for Master Brilic's three sixty-piece orbits."""
import json
from pathlib import Path
import sys
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import piece_orbits,apply_word
from solver.polyhedral_reduction import primitives
from solver.polyhedral_reduction import Transports
from solver.lattice_data import geometry_key


def run():
    cube=PolyhedralPuzzle('master_brilic',3);g=cube.geometry
    targets={i:o for i,o in enumerate(piece_orbits(cube.puzzle_kind,3)) if len(o)==60}
    words=primitives(cube,targets,use_prepared=False,deep=True,
                     progress=lambda done,total:print('discovery',done,total,flush=True) if done%2048==0 else None)
    records={}
    for index,(word,base) in words.items():
        permutation=apply_word(g,word);orbit=set(targets[index])
        moved={p for p,slots in enumerate(g.pieces) if any(permutation[s]!=s for s in slots)}
        if moved!=set(base) or len(moved)!=3 or not moved<=orbit:
            raise ValueError('Master Brilic primitive is not isolated')
        for a,b in zip(base,base[1:]+base[:1]):
            if {permutation[s] for s in g.pieces[a]}!=set(g.pieces[b]):
                raise ValueError('Master Brilic primitive splits a piece')
        if any(permutation[permutation[permutation[s]]]!=s for s in range(len(g.stickers))):
            raise ValueError('Master Brilic primitive has an extra orientation action')
        records[str(index)]=dict(base=base,word=[(m.axis,m.layer,m.amount) for m in word])
        transport=Transports(cube,targets[index],base)
        while transport._expand():pass
        reachable=int((transport.parents>=0).sum())
        if reachable!=60*59*58//3:raise ValueError('Brilic does not transport every ordered three-cycle')
        print('verified',index,len(word),base,'triple coverage',reachable,flush=True)
    if set(map(int,records))!=set(targets):raise ValueError('Missing Master Brilic orbit')
    path=Path('solver/data/master_brilic_cycles.bin')
    path.write_bytes(zlib.compress(json.dumps(dict(version=1,geometry=geometry_key(g),cycles=records),
                                             separators=(',',':')).encode(),9))
    print('SAVED',path,path.stat().st_size,flush=True)


if __name__=='__main__':run()
