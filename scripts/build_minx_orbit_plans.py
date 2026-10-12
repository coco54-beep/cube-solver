"""Precompute and certify the orbit plan used by native minx reduction."""
import argparse
import json
import sys
from pathlib import Path
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cube.polyhedral import PolyhedralPuzzle
from solver.lattice_data import geometry_key
from solver.polyhedral import apply_word,piece_orbits
from solver.high_minx_reduction import primitives,_macro_cost,_SHORT_PRIMITIVE


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--orders',type=int,nargs='+',default=list(range(4,14)))
    args=parser.parse_args()
    path=ROOT/'solver/data/minx_orbit_plans.bin'
    records=json.loads(zlib.decompress(path.read_bytes())) if path.exists() else {}
    for n in args.orders:
        cube=PolyhedralPuzzle('megaminx',n);g=cube.geometry
        targets={i:o for i,o in enumerate(piece_orbits('megaminx',n)) if len(o)>1}
        baseline=primitives(cube,targets,use_prepared=False)
        selected=baseline;order=list(targets);staged_selected=False
        if any(len(word)>_SHORT_PRIMITIVE for word,_ in baseline.values()):
            candidate_order=sorted(targets,key=lambda i:-len(baseline[i][0]))
            guarded=set();protected={}
            for i in candidate_order:
                protected[i]=set(guarded)
                guarded.update(s for p in targets[i] for s in g.pieces[p])
            try:
                staged=primitives(cube,targets,use_prepared=False,protected=protected)
            except ValueError:
                staged=None
            if staged is not None and _macro_cost(staged)<_macro_cost(baseline):
                selected=staged;order=candidate_order;staged_selected=True
        guarded=set()
        for i in order:
            word,base=selected[i];action=apply_word(g,word)
            moved=[p for p in targets[i] if g.stickers[action[g.pieces[p][0]]].piece!=p]
            assert len(moved)==3 and set(moved)==set(base),(n,i,'cycle support')
            a,b,c=base
            assert [g.stickers[action[g.pieces[p][0]]].piece for p in base]==[b,c,a],(n,i,'cycle direction')
            must_return=guarded if staged_selected else set(range(len(g.stickers)))-{
                s for p in targets[i] for s in g.pieces[p]}
            assert all(action[s]==s for s in must_return),(n,i,'protected stickers')
            guarded.update(s for p in targets[i] for s in g.pieces[p])
        records[str(n)]={'geometry':geometry_key(g),'order':order,'staged':staged_selected,
            'macros':{str(i):{'base':list(base),'word':[[m.axis,m.layer,m.amount] for m in word]}
                      for i,(word,base) in selected.items()}}
        temporary=path.with_suffix('.bin.tmp')
        temporary.write_bytes(zlib.compress(json.dumps(records,separators=(',',':')).encode(),9))
        temporary.replace(path)
        print(f'{n}: {len(targets)} certified macros, staged={staged_selected}, bytes={path.stat().st_size}',flush=True)


if __name__=='__main__':main()
