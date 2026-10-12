"""Bundle overcomplete conjugate words for the mod-2 core orientation.

The stored edge-orientation relations form a basis, so the runtime solve uses
about fifteen of their long words for a typical target. Conjugating each
relation by every legal turn produces a heavily overcomplete set of pure
kernel words; because the kernel has dimension twenty-nine this set has a
large null space and a target can be written as a handful of conjugates. The
generators are precomputed here so the phone does not rebuild them.
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
    generators={}
    for relation in core['relations']['2']:
        base=tuple(Move(*m) for m in relation['word'])
        for atom in (None,)+atoms:
            word=base if atom is None else simplify((atom.inverse(5),)+base+(atom,),5)
            full=apply_word(g,word)
            permutation=tuple(ids[full[s]] for s in points)
            try:
                vector=orientation_vector(permutation,units)[2]
            except ValueError:
                continue
            if not any(vector):
                continue
            key=0
            for i,value in enumerate(vector):
                key|=(value&1)<<i
            current=generators.get(key)
            if current is None or len(word)<len(current):
                generators[key]=word
    ordered=sorted(generators.items(),key=lambda entry:len(entry[1]))
    return ordered


def build():
    records={}
    for order in (3,5):
        print('Preparing edge generators',order,flush=True)
        ordered=generate(order)
        g=PolyhedralPuzzle('icosahedron',order).geometry
        records[str(order)]={'geometry':geometry_key(g),
            'generators':[[key,[[m.axis,m.layer,m.amount] for m in word]]
                          for key,word in ordered]}
        print('  ',order,len(ordered),'generators',flush=True)
    path=ROOT/'solver'/'data'/'icosahedron_edges.bin'
    path.write_bytes(zlib.compress(json.dumps(records,separators=(',',':')).encode('utf-8'),9))
    print('Saved',path,flush=True)


if __name__=='__main__':
    build()
