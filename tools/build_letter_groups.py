"""Compact certified stabilizers for the free letter-cube extensions."""
from pathlib import Path
import json
import zlib
from sympy.combinatorics import Permutation,PermutationGroup
from cube.polyhedral import Move
from solver.polyhedral import simplify,inverse_word,apply_word
from solver.cuboid_extensions import extension_mechanism
from tools.weighted_group_builder import build


def run(kind):
    adapter,panels,_,_=extension_mechanism(kind);g=adapter.geometry;order=g.spec.turn_order
    pool={g.permutation(m):((m.axis,m.layer,m.amount),) for m in adapter.moves()}
    group=PermutationGroup([Permutation(p) for p in pool]);base=list(reversed(range(len(panels))))
    group._schreier_sims(base=base)
    def compact(raw):return tuple((m.axis,m.layer,m.amount) for m in simplify(tuple(Move(*m) for m in raw),order))
    def backwards(raw):return tuple((m.axis,m.layer,m.amount) for m in inverse_word(tuple(Move(*m) for m in raw),order))
    records=build(pool,base,group.basic_orbits,group.orbits(),compact,backwards,limit=500,
                  report=lambda *a:print(kind,'group',*a,flush=True),preserve_group=True)
    for row in records:
        for record in row.values():
            if apply_word(g,tuple(Move(*m) for m in record['word']))!=tuple(record['permutation']):
                raise ValueError('Extension word failed exact replay')
    data=dict(version=1,kind=kind,fingerprint=adapter.fingerprint,order=str(group.order()),
              base=base,transversals=records)
    path=Path('solver/data')/(kind+'_extension_group.bin')
    path.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',path,path.stat().st_size,flush=True)
