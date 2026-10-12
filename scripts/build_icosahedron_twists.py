"""Bundle overcomplete twist words for the mod-5 core orientation.

The corner-twist kernel is twelve-dimensional. Eleven stored relations have a
coordinate sum of zero and their conjugates keep that sum, so they span only
the eleven-dimensional "sum zero" subspace; the remaining relation carries the
sum direction. The runtime therefore fixes the sum with one long relation and
then solves the sum-zero remainder with the short conjugates. This script
prepares both families so the phone does not rebuild them.
"""
from pathlib import Path
import json
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cube.polyhedral import Move, PolyhedralPuzzle
from solver.icosahedron import (core_points, orientation_units, orientation_vector,
                               _cores)
from solver.polyhedral import apply_word, simplify
from solver.lattice_data import geometry_key


def generate(order):
    cube=PolyhedralPuzzle('icosahedron',order)
    g=cube.geometry
    points=core_points(cube)
    ids={s:i for i,s in enumerate(points)}
    units=orientation_units(cube,points)
    core=_cores()[str(order)]
    atoms=tuple(Move(m.axis,m.layer,p*g.spec.step(m.axis))
                for m in cube.moves() for p in range(1,g.spec.order(m.axis)))
    short={}
    long_={}
    for relation in core['relations']['5']:
        word=tuple(Move(*m) for m in relation['word'])
        table=short if sum(relation['vector'])%5==0 else long_
        for atom in (None,)+atoms:
            candidate=word if atom is None else simplify((atom.inverse(5),)+word+(atom,),5)
            full=apply_word(g,candidate)
            permutation=tuple(ids[full[s]] for s in points)
            try:
                vector=orientation_vector(permutation,units)[5]
            except ValueError:
                continue
            if not any(vector):
                continue
            current=table.get(vector)
            if current is None or len(candidate)<len(current):
                table[vector]=candidate
    encode=lambda table:[[list(v),[[m.axis,m.layer,m.amount] for m in w]]
                         for v,w in sorted(table.items(),key=lambda entry:len(entry[1]))]
    return encode(short),encode(long_)


def build():
    records={}
    for order in (2,3,4,5):
        print('Preparing twist generators',order,flush=True)
        short,long_=generate(order)
        g=PolyhedralPuzzle('icosahedron',order).geometry
        records[str(order)]={'geometry':geometry_key(g),'short':short,'long':long_}
        print('  ',order,'short',len(short),'long',len(long_),flush=True)
    path=ROOT/'solver'/'data'/'icosahedron_twists.bin'
    path.write_bytes(zlib.compress(json.dumps(records,separators=(',',':')).encode('utf-8'),9))
    print('Saved',path,flush=True)


if __name__=='__main__':
    build()
