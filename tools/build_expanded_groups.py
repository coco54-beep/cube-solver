"""Offline short-word groups for the newly specified fixed-slot mechanisms."""
import argparse
import json
from pathlib import Path
import sys
from time import monotonic
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sympy.combinatorics import Permutation,PermutationGroup
from candidate_puzzles import BY_KIND
from cube.polyhedral import PolyhedralPuzzle,Move
from solver.polyhedral import simplify,inverse_word,apply_word
from solver.lattice_data import geometry_key
from tools.weighted_group_builder import build


def run(kind):
    if kind=='master_brilic':
        from tools.build_master_brilic import run as build_cycles
        return build_cycles()
    started=monotonic();entry=BY_KIND[kind];cube=PolyhedralPuzzle(kind,entry.n);g=cube.geometry
    def compact(raw):return tuple((m.axis,m.layer,m.amount) for m in simplify(tuple(Move(*m) for m in raw),g.spec.turn_order))
    def backwards(raw):return tuple((m.axis,m.layer,m.amount) for m in inverse_word(tuple(Move(*m) for m in raw),g.spec.turn_order))
    pool={}
    for move in cube.moves():
        for amount in range(g.spec.step(move.axis),g.spec.turn_order,g.spec.step(move.axis)):
            atom=Move(move.axis,move.layer,amount);p=g.permutation(atom)
            pool[p]=((atom.axis,atom.layer,atom.amount),)
    group=PermutationGroup([Permutation(p) for p in pool])
    # Keep the descending full base: the runtime matches colours in this
    # order, including fixed facets, without inventing identities for them.
    base=list(reversed(range(len(g.stickers))))
    group._schreier_sims(base=base)
    if group.base!=base:raise ValueError('Expanded base was unexpectedly changed')
    print(kind,'order',group.order(),'degree',len(base),flush=True)
    def odd(p,orbit):
        seen=set();cycles=0
        for start in orbit:
            if start in seen:continue
            cycles+=1;j=start
            while j not in seen:seen.add(j);j=p[j]
        return (len(orbit)-cycles)%2
    # Tiny orientation orbits such as Starminx's twenty C3 corners are
    # always even. They carry no parity character and need no mask bit.
    parity_orbits=[o for o in group.orbits() if len(o)>1 and any(odd(p,o) for p in pool)]
    records=build(pool,base,group.basic_orbits,parity_orbits,compact,backwards,
                  report=lambda level,size,longest,count:print(kind,level,size,longest,count,flush=True),
                  preserve_group=True)
    verified=0
    for row in records:
        for entry in row.values():
            if apply_word(g,tuple(Move(*m) for m in entry['word']))!=tuple(entry['permutation']):
                raise ValueError('Expanded transversal word does not match its action')
            verified+=1
    data=dict(version=1,kind=kind,n=cube.n,geometry=geometry_key(g),order=str(group.order()),
              base=base,transversals=records,verified_transversals=verified)
    target=Path('solver/data')/(kind+'_expanded_group.bin')
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',kind,target.stat().st_size,'bytes',verified,'verified',round(monotonic()-started,3),'seconds',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('kinds',nargs='*',default=['rubik_cheese','pyraminx_diamond','masterball'])
    for name in parser.parse_args().kinds:run(name)
