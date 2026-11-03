"""Certify short transversals of the private closed-shape Copter action."""
import sys,json,zlib
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sympy.combinatorics import Permutation,PermutationGroup
from cube.copter_aligned import AlignedCopter,generators,source_key
from cube.polyhedral import Move
from solver.polyhedral import simplify,apply_word
from solver.lattice_data import geometry_key
from tools.weighted_group_builder import build


def run():
    start=monotonic();cube=AlignedCopter();g=cube.geometry
    pool={action:((i,0,1),) for i,(action,word) in enumerate(generators())}
    group=PermutationGroup([Permutation(p) for p in pool])
    # Unique corners and individually anchored edges are sifted before the
    # freely interchangeable same-colour leaves. All 72 panel points remain
    # in the certified base, even if a base point is already fixed.
    base=sorted(range(72),key=lambda s:(-len(g.pieces[g.stickers[s].piece]),-s))
    group._schreier_sims(base=base)
    if group.base!=base:raise ValueError('Unexpected Copter colour base')
    print('order',group.order(),'generators',len(pool),'base',base,flush=True)
    def compact(raw):return tuple((m.axis,0,m.amount) for m in simplify(tuple(Move(*m) for m in raw),2))
    def backwards(raw):return tuple(reversed(raw))
    def odd(p,orbit):
        ids=sorted(orbit);local={s:i for i,s in enumerate(ids)}
        values=[local[p[s]] for s in ids]
        return sum(values[i]>v for i in range(len(values)) for v in values[i+1:])%2
    parity=[o for o in group.orbits() if len(o)>1 and any(odd(p,o) for p in pool)]
    records=build(pool,base,group.basic_orbits,parity,compact,backwards,preserve_group=True,
                  limit=1500,bucket_limit=1500,
                  report=lambda *row:print(*row,flush=True))
    verified=0
    for row in records:
        for data in row.values():
            if apply_word(g,tuple(Move(*m) for m in data['word']))!=tuple(data['permutation']):
                raise ValueError('Copter transversal word/action mismatch')
            verified+=1
    data=dict(version=1,geometry=geometry_key(g),source=source_key(),base=base,order=str(group.order()),
              macros=[[(m.axis,m.layer,m.amount) for m in word] for action,word in generators()],
              verified_transversals=verified,transversals=records)
    target=Path('solver/data/curvy_copter_colour_group.bin');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',target,target.stat().st_size,'bytes',verified,'entries','seconds',round(monotonic()-start,2),flush=True)


if __name__=='__main__':run()
