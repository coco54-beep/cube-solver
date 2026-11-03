"""Build and exhaustively certify AJ's small staged-cycle asset."""
import json
from pathlib import Path
import sys
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle,Move
from solver.polyhedral import piece_orbits,apply_word
from solver.polyhedral_reduction import primitives,Transports
from solver.lattice_data import geometry_key
from tools.build_rex_cycles import flip_pair


def run():
    cube=PolyhedralPuzzle('aj_curvy_dinominx_4',4);g=cube.geometry
    orbits=piece_orbits(cube.puzzle_kind,4)
    order=sorted((i for i,o in enumerate(orbits) if len(o)>1),key=lambda i:len(orbits[i]))
    prior={s for o in orbits if len(o)==1 for p in o for s in g.pieces[p]}
    protected={}
    for i in order:
        protected[i]=set(prior);prior.update(s for p in orbits[i] for s in g.pieces[p])
    macros=primitives(cube,{i:orbits[i] for i in order},use_prepared=False,protected=protected)
    cycles={};coverage={}
    for i in order:
        word,base=macros[i];effect=apply_word(g,word)
        assert all(effect[s]==s for s in protected[i])
        transport=Transports(cube,orbits[i],base)
        while transport._expand():pass
        reachable=int((transport.parents>=0).sum())
        expected=len(orbits[i])*(len(orbits[i])-1)*(len(orbits[i])-2)//3
        if reachable!=expected:raise ValueError('AJ cycle lacks full directed triple coverage')
        coverage[str(i)]=reachable
        cycles[str(i)]=dict(word=[(m.axis,m.layer,m.amount) for m in word],base=base)
        print('stage',i,'size',len(orbits[i]),'macro',len(word),'coverage',reachable,flush=True)
    flip=flip_pair(cube,orbits[order[0]])
    action=apply_word(g,tuple(Move(*m) for m in flip['word']))
    if any(action[s]!=s for s in protected[order[0]]):raise ValueError('Edge flip disturbs fixed caps')
    data=dict(version=1,kind=cube.puzzle_kind,n=4,geometry=geometry_key(g),order=order,
              cycles=cycles,coverage=coverage,edge_flip=flip)
    path=Path('solver/data/aj_curvy_dinominx_4_cycles.bin')
    path.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',path,path.stat().st_size,flush=True)


if __name__=='__main__':run()
