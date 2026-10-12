"""Prepare short position cycles and linear orientation relations offline."""
from pathlib import Path
import json
import math
import random
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cube.polyhedral import PolyhedralPuzzle, Move
from solver.icosahedron import (PositionModel, core_points, orientation_units,
                               orientation_vector, independent_relation)
from solver.polyhedral import (StabilizerChain, apply_word, compose, inverse,
                              inverse_word, simplify)
from solver.polyhedral_reduction import primitives, Transports
from solver.lattice_data import geometry_key
from solver.nxn_orbits import three_cycles


def positions(cube):
    model=PositionModel(cube)
    targets=model.targets()
    try:
        return model,primitives(model,targets)
    except ValueError:
        if cube.n!=2:
            raise
    found=primitives(model,{0:targets[0]})
    g=model.geometry
    atoms=model.moves()
    maps={a:g.permutation(a) for a in atoms}
    transports=Transports(model,targets[0],found[0][1])
    # Search every anchor and keep the shortest pure centre three-cycle. The
    # original code returned the first match, leaving the order 2 centre macro
    # longer than necessary; this matters far more than the extra search time
    # because the same word closes the long orientation relation.
    best=None
    for a in atoms:
        for b in atoms:
            for c in atoms:
                for power in range(1,5):
                    bw=(Move(b.axis,b.layer,power),c,Move(b.axis,b.layer,5-power))
                    word=(a,)+bw+(a.inverse(5),)+inverse_word(bw,5)
                    p=apply_word(g,word)
                    for d in atoms:
                        cw=(d,)+word+(d.inverse(5),)
                        q=compose(compose(maps[d],p),inverse(maps[d]))
                        r=compose(compose(compose(p,q),inverse(p)),inverse(q))
                        moved=[i for i in targets[1] if r[i]!=i]
                        if len(moved)!=3 or any(r[i] not in moved for i in moved):
                            continue
                        corrected=list(word+cw+inverse_word(word,5)+inverse_word(cw,5))
                        orbit=targets[0]
                        ids={home:i for i,home in enumerate(orbit)}
                        destination=[None]*len(orbit)
                        for home in orbit:
                            destination[ids[r[home]]]=ids[home]
                        primitive,base=found[0]
                        for cycle in three_cycles(destination):
                            path=transports.path(tuple(orbit[i] for i in cycle))
                            correction=inverse_word(path,5)+primitive+path
                            r=compose(r,apply_word(g,correction))
                            corrected.extend(correction)
                        if any(r[i]!=i for i in orbit):
                            continue
                        shortened=simplify(corrected,5)
                        if best is None or len(shortened)<len(best[0]):
                            origin=moved[0]
                            best=(shortened,(origin,r[origin],r[r[origin]]))
    if best is None:
        raise ValueError('No short Icosamate centre cycle was found')
    found[1]=best
    print('order 2 centre macro',len(best[0]),flush=True)
    return model,found


def build():
    records={}
    for order in (2,3,4,5):
        cube=PolyhedralPuzzle('icosahedron',order)
        g=cube.geometry
        points=core_points(cube)
        print('Preparing core',order,len(points),flush=True)
        model,cycles=positions(cube)
        print('POSITION CYCLES',[(i,len(w)) for i,(w,b) in cycles.items()],flush=True)
        # Compare the exact group order; no scrambled states are sampled.
        chain=StabilizerChain(cube,points=points)
        group_size=math.prod(len(row) for row in chain.trans)
        position_size=math.prod(math.factorial(len(o))//2 for o in model.targets().values())
        kernel_size=group_size//position_size
        required={}
        for prime in (5,2):
            rank=0
            while kernel_size%prime==0:
                kernel_size//=prime
                rank+=1
            required[prime]=rank
        if kernel_size!=1 or group_size%position_size:
            raise ValueError('The core is not the expected alternating position group')
        units=orientation_units(cube,points)
        ids={s:i for i,s in enumerate(points)}
        atoms=cube.moves()
        maps={a:tuple(ids[g.permutation(a)[s]] for s in points) for a in atoms}
        bases={5:{},2:{}}
        relations={5:[],2:[]}
        queue=[]
        identity=tuple(range(len(points)))

        def add(p,word):
            vector=orientation_vector(p,units)
            for prime in (5,2):
                v=vector[prime]
                power=2 if prime==5 else 5
                v=tuple((x*power)%prime for x in v)
                if independent_relation(v,bases[prime],prime):
                    relations[prime].append((v,simplify(word*power,5)))
                    queue.append((prime,p,word))
                    print('RANK',order,prime,len(relations[prime]),required[prime],flush=True)

        for word,_ in cycles.values():
            full=apply_word(g,word)
            p=tuple(ids[full[s]] for s in points)
            add(compose(compose(p,p),p),word*3)
        comm_candidates=[]
        for a in atoms:
            for b in atoms:
                if a.axis==b.axis:
                    continue
                word=(a,b,a.inverse(5),b.inverse(5))
                p=compose(compose(compose(maps[a],maps[b]),inverse(maps[a])),inverse(maps[b]))
                pp=model.geometry.permutation(a)
                qq=model.geometry.permutation(b)
                projected=compose(compose(compose(pp,qq),inverse(pp)),inverse(qq))
                lengths=[]
                seen=set()
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
                comm_candidates.append((4*power,powered,word*power))
        # Shortest relations first: greedily pick independent ones so the stored
        # words stay compact instead of using whichever was found first.
        comm_candidates.sort(key=lambda entry:entry[0])
        for _length,powered,comm_word in comm_candidates:
            if all(len(relations[p])==required[p] for p in (5,2)):
                break
            add(powered,comm_word)
        # Commutators have zero total corner rotation. A short group
        # relation with a nonzero exponent sum supplies that last dimension.
        rng=random.Random(82673)
        for _ in range(1000):
            if len(relations[5])==required[5]:
                break
            word=tuple(rng.choice(atoms) for _ in range(rng.randrange(2,7)))
            projected=apply_word(model.geometry,word)
            lengths=[]
            seen=set()
            for start in range(len(projected)):
                if start in seen:
                    continue
                j=start; length=0
                while j not in seen:
                    seen.add(j); length+=1; j=projected[j]
                lengths.append(length)
            power=math.lcm(*lengths)
            if power%5==0 or power>120:
                continue
            full=apply_word(g,word)
            p=tuple(ids[full[s]] for s in points)
            powered=identity
            for _ in range(power):
                powered=compose(powered,p)
            add(powered,word*power)
        transports={i:Transports(model,orbit,cycles[i][1]) for i,orbit in model.targets().items()}
        atom_relations=[]
        for a in atoms:
            projected=model.geometry.permutation(a)
            word=[a]
            for index,orbit in model.targets().items():
                indexes={home:i for i,home in enumerate(orbit)}
                destination=[None]*len(orbit)
                for home in orbit:
                    destination[indexes[projected[home]]]=indexes[home]
                primitive,base=cycles[index]
                for cycle in three_cycles(destination):
                    path=transports[index].path(tuple(orbit[i] for i in cycle))
                    correction=inverse_word(path,5)+primitive+path
                    projected=compose(projected,apply_word(model.geometry,correction))
                    word.extend(correction)
            if projected!=tuple(range(len(projected))):
                raise ValueError('Position relation is not closed')
            word=simplify(word,5)
            full=apply_word(g,word)
            atom_relations.append((len(word),tuple(ids[full[s]] for s in points),word))
        # Shortest single-atom relations first, again greedy by independence.
        atom_relations.sort(key=lambda entry:entry[0])
        for _length,perm,word in atom_relations:
            if all(len(relations[p])==required[p] for p in (5,2)):
                break
            add(perm,word)
        cursor=0
        while cursor<len(queue) and any(len(relations[p])<required[p] for p in (5,2)):
            prime,p,word=queue[cursor]
            cursor+=1
            if len(relations[prime])==required[prime]:
                continue
            for a in atoms:
                q=compose(compose(maps[a],p),inverse(maps[a]))
                add(q,(a,)+word+(a.inverse(5),))
        if any(len(relations[p])!=required[p] for p in (5,2)):
            raise ValueError('Orientation relations do not span the full core kernel')
        records[str(order)]={'geometry':geometry_key(g),
          'position_cycles':{str(i):{'word':[[m.axis,m.layer,m.amount] for m in w],
                                    'base':[model.originals[p] for p in b]}
                             for i,(w,b) in cycles.items()},
          'relations':{str(prime):[{'vector':list(v),'word':[[m.axis,m.layer,m.amount] for m in w]}
                                   for v,w in relations[prime]] for prime in (5,2)}}
        path=ROOT/'solver'/'data'/'icosahedron_core.bin'
        path.write_bytes(zlib.compress(json.dumps(records,separators=(',',':')).encode('utf-8'),9))
        print('Saved core',order,path,flush=True)


if __name__=='__main__':
    build()
