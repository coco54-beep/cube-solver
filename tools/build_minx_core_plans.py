"""Prepare and verify high-minx centre macros on a computer, not a phone."""
import argparse
import json
import os
from pathlib import Path
import zlib

from cube.polyhedral import PolyhedralPuzzle
from solver.lattice_data import geometry_key
from solver.polyhedral import apply_word, piece_orbits
from solver.polyhedral_reduction import _macro_cost, primitives


def commutator_primitive(cube,orbit,fixed):
    """Fast scan for a four-move commutator that cycles exactly three pieces.

    ``fixed`` is the sticker set the macro must leave untouched. Returns
    ``(word, base)`` or None. The scan is cheap because most pairs are rejected
    by the two fixed-sticker probes below.
    """
    g=cube.geometry
    order=g.spec.turn_order
    atoms=cube.moves()
    inverses={m:m.inverse(order) for m in atoms}
    target_pieces=set(orbit)
    for a in atoms:
        ai=inverses[a]
        for b in atoms:
            if a.axis==b.axis:
                continue
            word=(a,b,ai,inverses[b])
            permutation=apply_word(g,word)
            if any(permutation[s]!=s for s in fixed):
                continue
            moved={p for p in target_pieces
                   if g.stickers[permutation[g.pieces[p][0]]].piece!=p}
            if len(moved)!=3:
                continue
            first=next(iter(moved))
            def image(p):
                return g.stickers[permutation[g.pieces[p][0]]].piece
            base=(first,image(first),image(image(first)))
            if len(set(base))!=3:
                continue
            return word,base
    return None


def prepare(n):
    cube=PolyhedralPuzzle.solved('megaminx',n)
    g=cube.geometry
    orbits=piece_orbits('megaminx',n)
    core={i for i,o in enumerate(orbits) if len(g.pieces[o[0]])==3 or
          (len(o)==30 and len(g.pieces[o[0]])==2)}
    targets={i:o for i,o in enumerate(orbits) if len(o)>1 and i not in core}
    everything=set(range(len(g.stickers)))
    baseline={}
    missing={}
    for index,orbit in targets.items():
        orbit_stickers={s for p in orbit for s in g.pieces[p]}
        found=commutator_primitive(cube,orbit,everything-orbit_stickers)
        if found is None:
            missing[index]=orbit
        else:
            baseline[index]=found
    if missing:
        baseline.update(primitives(cube,missing))
    order=sorted(targets,key=lambda i:-len(baseline[i][0]))
    guarded={s for i in core for p in orbits[i] for s in g.pieces[p]}
    protected={}
    for index in order:
        protected[index]=set(guarded)
        guarded.update(s for p in targets[index] for s in g.pieces[p])
    staged={}
    missing={}
    for index in order:
        found=commutator_primitive(cube,targets[index],protected[index])
        if found is None:
            missing[index]=targets[index]
        else:
            staged[index]=found
    if missing:
        try:
            staged.update(primitives(cube,missing,
                                     protected={i:protected[i] for i in missing}))
        except ValueError:
            pass
    use_staged=bool(staged) and _macro_cost(staged)<_macro_cost(baseline)
    macros=staged if use_staged else baseline
    for index,(word,base) in macros.items():
        permutation=apply_word(g,word)
        moving={s for p in targets[index] for s in g.pieces[p]}
        fixed=protected[index] if use_staged else set(range(len(g.stickers)))-moving
        assert all(permutation[s]==s for s in fixed), (n,index,'protected stickers')
        moved={p for p in targets[index]
               if g.stickers[permutation[g.pieces[p][0]]].piece!=p}
        assert moved==set(base) and len(moved)==3, (n,index,'cycle support')
        assert all(g.stickers[permutation[g.pieces[a][0]]].piece==b
                   for a,b in zip(base,base[1:]+base[:1])), (n,index,'cycle direction')
    return geometry_key(g), {'order':order,'staged':use_staged,
        'macros':{str(i):{'word':[[m.axis,m.layer,m.amount] for m in word],
                          'base':list(base)} for i,(word,base) in macros.items()}}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('orders',nargs='*',type=int,default=list(range(4,14)))
    args=parser.parse_args()
    path=Path(__file__).resolve().parents[1]/'solver/data/minx_orbit_plans.bin'
    data=json.loads(zlib.decompress(path.read_bytes()))
    for n in args.orders:
        print('Preparing',n,flush=True)
        key,plan=prepare(n)
        assert data[str(n)]['geometry']==key, (n,'geometry mismatch')
        data[str(n)]['core_plan']=plan
        # Atomic per-order checkpoints allow interrupted offline builds to resume.
        temporary=path.with_suffix('.tmp')
        temporary.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
        os.replace(temporary,path)
        print('Verified',n,len(plan['macros']),'orbits; staged =',plan['staged'],flush=True)


if __name__=='__main__': main()
