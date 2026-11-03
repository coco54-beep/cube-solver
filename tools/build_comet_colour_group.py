"""Build and independently replay the aligned Comet stabilizer chain."""
import sys,json,zlib
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sympy.combinatorics import Permutation,PermutationGroup
from cube.comet_aligned import AlignedComet,generators,source_key
from cube.polyhedral import Move
from solver.polyhedral import simplify,apply_word
from solver.lattice_data import geometry_key
from tools.weighted_group_builder import build

PHYSICAL='--physical' in sys.argv
if PHYSICAL:
    from cube.lanlan_comet_aligned import AlignedComet,generators,source_key


def run():
    start=monotonic();cube=AlignedComet();g=cube.geometry
    pool={action:((i,0,1),) for i,(action,word) in enumerate(generators())}
    group=PermutationGroup([Permutation(p) for p in pool]);base=sorted(range(len(cube.colors)),
        key=lambda s:(-len(g.pieces[g.stickers[s].piece]),-s))
    group._schreier_sims(base=base)
    if group.base!=base:raise ValueError('Unexpected Comet base')
    print('order',group.order(),'orbits',[len(o) for o in group.orbits()],flush=True)
    def compact(raw):return tuple((m.axis,0,m.amount) for m in simplify(tuple(Move(*m) for m in raw),2))
    def odd(p,orbit):
        ids=sorted(orbit);local={s:i for i,s in enumerate(ids)};values=[local[p[s]] for s in ids]
        return sum(values[i]>v for i in range(len(values)) for v in values[i+1:])%2
    parity=[o for o in group.orbits() if len(o)>1 and any(odd(p,o) for p in pool)]
    records=build(pool,base,group.basic_orbits,parity,compact,lambda raw:tuple(reversed(raw)),
                  preserve_group=True,limit=100 if PHYSICAL else 1000,bucket_limit=100 if PHYSICAL else 1000,
                  report=lambda *row:print(*row,flush=True))
    verified=0
    for row in records:
        for record in row.values():
            if apply_word(g,tuple(Move(*m) for m in record['word']))!=tuple(record['permutation']):
                raise ValueError('Comet word/action mismatch')
            verified+=1
    data=dict(version=1,geometry=geometry_key(g),source=source_key(),base=base,order=str(group.order()),
              macros=[[(m.axis,m.layer,m.amount) for m in word] for action,word in generators()],
              verified_transversals=verified,transversals=records)
    target=Path('solver/data/lanlan_comet_colour_group.bin' if PHYSICAL else 'solver/data/crazy_comet_colour_group.bin')
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',target,target.stat().st_size,verified,'seconds',round(monotonic()-start,2),flush=True)


if __name__=='__main__':run()
