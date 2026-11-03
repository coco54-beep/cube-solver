"""Compile a small certified observed-colour solver for Pisces circuits."""
import sys,json,zlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.pisces_aligned import AlignedPisces,generators,source_key
from cube.polyhedral import Move
from tools.exact_group_certificate import Certificate
from tools.weighted_group_builder import build
from solver.polyhedral import simplify,inverse_word,apply_word
from solver.lattice_data import geometry_key


if __name__=='__main__':
    stem='pisces'
    if '--hexagram' in sys.argv:
        from cube.hexagram_aligned import AlignedHexagram as AlignedPisces,generators,source_key
        stem='hexagram'
    elif '--clover-pyraminx' in sys.argv:
        from cube.clover_pyraminx_aligned import AlignedCloverPyraminx as AlignedPisces,generators,source_key
        stem='clover_pyraminx'
    started=time.monotonic();c=AlignedPisces();g=c.geometry;order=g.spec.turn_order
    pool={a:((i,0,g.spec.step(i)),) for i,(a,w) in enumerate(generators())}
    base=sorted(range(len(c.colors)),key=lambda s:(-len(g.pieces[g.stickers[s].piece]),s))
    certificate=Certificate(len(base),base)
    for a in pool:certificate.add(a)
    print('GROUP',certificate.order,'actions',len(pool),flush=True)
    def compact(w):return tuple((m.axis,m.layer,m.amount) for m in simplify(tuple(Move(*m) for m in w),order))
    def backwards(w):return tuple((m.axis,m.layer,m.amount) for m in inverse_word(tuple(Move(*m) for m in w),order))
    records=build(pool,base,[tuple(row) for row in certificate.trans],[],compact,backwards,
                  preserve_group=True,limit=80,bucket_limit=80,report=lambda *r:print(*r,flush=True))
    verified=0
    for row in records:
        for record in row.values():
            assert apply_word(g,tuple(Move(*m) for m in record['word']))==tuple(record['permutation']);verified+=1
    data=dict(version=1,geometry=geometry_key(g),source=source_key(),base=base,order=str(certificate.order),
              transversals=records,verified_transversals=verified,
              macros=[[[m.axis,m.layer,m.amount] for m in w] for a,w in generators()])
    target=(Path('artifacts/research/clover-pyraminx/colour_group.bin') if stem=='clover_pyraminx'
            else Path('solver/data')/(stem+'_colour_group.bin'))
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',target.stat().st_size,'transversals',verified,'seconds',time.monotonic()-started,flush=True)
