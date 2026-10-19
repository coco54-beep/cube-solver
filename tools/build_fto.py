"""Prepare FTO core transversals and isolated orbit cycles for one order."""
import json
from pathlib import Path
import sys
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle
from solver.fto import core_points
from solver.lattice_data import geometry_key
from solver.polyhedral import StabilizerChain, apply_word, piece_orbits, simplify
from solver.polyhedral_reduction import primitives


def update_asset(name,n,record):
    path=Path(__file__).resolve().parents[1]/'solver/data'/name
    records=json.loads(zlib.decompress(path.read_bytes())) if path.exists() else {}
    records[str(n)]=record
    path.write_bytes(zlib.compress(json.dumps(records,separators=(',',':')).encode(),9))
    print(name,path.stat().st_size,'bytes',flush=True)


def build(n=5):
    cube=PolyhedralPuzzle('fto',n)
    g=cube.geometry
    points=core_points(cube)
    print('Preparing core:',len(points),'markers',flush=True)
    chain=StabilizerChain(cube,points=points)
    rows=[]
    for table in chain.trans:
        row={}
        for position,(permutation,word) in table.items():
            expanded=simplify(tuple(word.flatten(3)),3)
            full=apply_word(g,expanded)
            if tuple(points[permutation[i]] for i in range(len(points)))!=tuple(full[s] for s in points):
                raise ValueError('FTO core word does not match its permutation')
            row[str(position)]=(permutation,[(m.axis,m.layer,m.amount) for m in expanded])
        rows.append(row)
    update_asset('fto_core.bin',n,dict(geometry=geometry_key(g),points=points,rows=rows))
    targets={i:o for i,o in enumerate(piece_orbits('fto',n)) if len(o)>6 and len(g.pieces[o[0]])<3}
    print('Preparing isolated cycles:',len(targets),'orbits',flush=True)
    macros=primitives(cube,targets,use_prepared=False,deep=True)
    records={}
    for i,(word,base) in macros.items():
        permutation=apply_word(g,word)
        support={s for p in targets[i] for s in g.pieces[p]}
        if any(p!=s for s,p in enumerate(permutation) if s not in support):
            raise ValueError('FTO orbit word disturbs another orbit')
        moved=[p for p in targets[i] if g.stickers[permutation[g.pieces[p][0]]].piece!=p]
        if len(moved)!=3 or any(g.stickers[permutation[g.pieces[base[j]][0]]].piece!=base[(j+1)%3] for j in range(3)):
            raise ValueError('FTO orbit word is not the expected three-cycle')
        records[str(i)]=dict(word=[(m.axis,m.layer,m.amount) for m in word],base=base)
    order=sorted(targets,key=lambda i:-len(macros[i][0]))
    guarded=set(points)
    protected={}
    for i in order:
        protected[i]=set(guarded)
        guarded.update(s for p in targets[i] for s in g.pieces[p])
    print('Preparing shorter staged cycles',flush=True)
    staged=primitives(cube,targets,use_prepared=False,deep=True,protected=protected)
    stage_records={}
    for i,(word,base) in staged.items():
        permutation=apply_word(g,word)
        if any(permutation[s]!=s for s in protected[i]):
            raise ValueError('FTO staged cycle disturbs a completed stage')
        moved=[p for p in targets[i] if g.stickers[permutation[g.pieces[p][0]]].piece!=p]
        if len(moved)!=3 or any(g.stickers[permutation[g.pieces[base[j]][0]]].piece!=base[(j+1)%3] for j in range(3)):
            raise ValueError('FTO staged cycle is not the expected three-cycle')
        stage_records[str(i)]=dict(word=[(m.axis,m.layer,m.amount) for m in word],base=base)
    update_asset('fto_cycles.bin',n,dict(geometry=geometry_key(g),cycles=records,
                                      stage_order=order,staged=stage_records))
    print('Prepared cycle lengths:',{i:len(w) for i,(w,_) in macros.items()},flush=True)
    print('Staged cycle lengths:',{i:len(w) for i,(w,_) in staged.items()},flush=True)


if __name__=='__main__': build(int(sys.argv[1]) if len(sys.argv)>1 else 5)
