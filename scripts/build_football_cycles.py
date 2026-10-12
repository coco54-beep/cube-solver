"""Generate state-independent Tuttminx cycles and edge flip relations."""
from pathlib import Path
import json
import math
import sys
import zlib
import argparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cube.polyhedral import PolyhedralPuzzle, Move
from solver.football import EdgePositions, edge_orbit, edge_units
from solver.icosahedron import orientation_vector, independent_relation
from solver.polyhedral import (piece_orbits, apply_word, compose, inverse,
                              inverse_word, simplify)
from solver.polyhedral_reduction import primitives, Transports
from solver.lattice_data import geometry_key
from solver.nxn_orbits import three_cycles


def encoded(word):
    return [[m.axis,m.layer,m.amount] for m in word]


def flip_relations(cube,model,cycle):
    g=cube.geometry
    points,units=edge_units(cube)
    ids={s:i for i,s in enumerate(points)}
    atoms=cube.moves()
    maps={m:tuple(ids[g.permutation(m)[s]] for s in points) for m in atoms}
    identity=tuple(range(len(points)))
    basis={}
    relations=[]
    queue=[]
    def add(p,word):
        vector=orientation_vector(p,units)[2]
        if sum(vector)%2:
            raise ValueError('A Tuttminx relation violates the even edge-flip constraint')
        if independent_relation(vector,basis,2):
            relations.append({'vector':list(vector),'word':encoded(simplify(word,15))})
            queue.append((p,word))
            print('FLIP RANK',len(relations),29,flush=True)
    word,base=cycle
    full=apply_word(g,word*3)
    add(tuple(ids[full[s]] for s in points),word*3)
    for a in atoms:
        for b in atoms:
            if a.axis==b.axis or len(relations)==29:
                continue
            word=(a,b,a.inverse(15),b.inverse(15))
            p=compose(compose(compose(maps[a],maps[b]),inverse(maps[a])),inverse(maps[b]))
            projected=apply_word(model.geometry,word)
            seen=set(); lengths=[]
            for start in range(len(projected)):
                if start in seen:
                    continue
                j=start; length=0
                while j not in seen:
                    seen.add(j); length+=1; j=projected[j]
                lengths.append(length)
            power=math.lcm(*lengths)
            if power>60:
                continue
            powered=identity
            for _ in range(power):
                powered=compose(powered,p)
            add(powered,word*power)
    transports=Transports(model,tuple(range(len(model.originals))),base)
    for atom in atoms:
        if len(relations)==29:
            break
        projected=model.geometry.permutation(atom)
        word=[atom]
        destination=[None]*len(projected)
        for home,position in enumerate(projected):
            destination[position]=home
        for target in three_cycles(destination):
            path=transports.path(target)
            correction=inverse_word(path,15)+cycle[0]+path
            projected=compose(projected,apply_word(model.geometry,correction))
            word.extend(correction)
        if projected!=tuple(range(len(projected))):
            raise ValueError('Tuttminx edge position relation is not closed')
        full=apply_word(g,word)
        add(tuple(ids[full[s]] for s in points),tuple(word))
    cursor=0
    while cursor<len(queue) and len(relations)<29:
        p,word=queue[cursor]; cursor+=1
        for atom in atoms:
            conjugated=compose(compose(maps[atom],p),inverse(maps[atom]))
            add(conjugated,(atom,)+word+(atom.inverse(15),))
            if len(relations)==29:
                break
    if len(relations)!=29:
        raise ValueError('Tuttminx edge flip relations do not span the even-flip kernel')
    return relations


def build(orders=(3,5)):
    path=ROOT/'solver'/'data'/'football_cycles.bin'
    records=json.loads(zlib.decompress(path.read_bytes())) if path.exists() else {}
    records={key:record for key,record in records.items() if key in ('3','5')}
    for order in orders:
        cube=PolyhedralPuzzle('football',order)
        g=cube.geometry
        orbits=piece_orbits('football',order)
        targets={i:o for i,o in enumerate(orbits) if len(o)==60}
        print('Preparing Tuttminx',order,len(targets),'orbits',flush=True)
        # Rank the orbits by how hard they are to isolate on their own. The
        # hardest go first, while almost nothing is solved yet, so their macros
        # may be short and disturb the still-unsolved orbits. Because piece
        # orbits are invariant under every turn, a macro that fixes the union
        # of already-solved orbits survives conjugation by any setup.
        baseline=primitives(cube,targets)
        solve_order=sorted(targets,key=lambda i:-len(baseline[i][0]))
        protected={}
        guarded=set()
        if edge_orbit(cube) is not None:
            # The core edge orbit is positioned and flipped before the rest.
            guarded.update(edge_units(cube)[0])
        for index in solve_order:
            protected[index]=set(guarded)
            guarded.update(s for p in targets[index] for s in g.pieces[p])
        cycles=primitives(cube,targets,protected=protected)
        for index,(word,base) in cycles.items():
            print('CYCLE',order,index,len(word),flush=True)
        record={'geometry':geometry_key(g),
                'order':solve_order,
                'cycles':{str(i):{'word':encoded(w),'base':list(b)} for i,(w,b) in cycles.items()}}
        if edge_orbit(cube) is not None:
            model=EdgePositions(cube)
            cycle=primitives(model,{0:tuple(range(len(model.originals)))},anchor_axis=12)[0]
            record['edge_cycle']={'word':encoded(cycle[0]),
                                  'base':[model.originals[p] for p in cycle[1]]}
            record['edge_flips']=flip_relations(cube,model,cycle)
        records[str(order)]=record
        temporary=path.with_suffix('.bin.tmp')
        temporary.write_bytes(zlib.compress(json.dumps(records,separators=(',',':')).encode('utf-8'),9))
        temporary.replace(path)
        print('Saved',order,path,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--orders',type=int,nargs='+',choices=(3,5),default=(3,5))
    build(parser.parse_args().orders)
