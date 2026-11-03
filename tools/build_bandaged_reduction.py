"""Exhaustive rigid-layout graph and its complete Schreier loop group."""
import json
import struct
import sys
import zlib
from collections import deque
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from sympy.combinatorics import Permutation,PermutationGroup
from solver.bandaged_reduction import geometry,inverse_word
from tools.weighted_group_builder import build,inverse


def compact(word):
    out=[]
    for token in word:
        amount=2 if token.endswith('2') else 3 if token.endswith("'") else 1
        face=token[:-1] if token.endswith(('2',"'")) else token
        if out:
            previous=out[-1];label=previous[:-1] if previous.endswith(('2',"'")) else previous
            if face==label:
                out.pop();amount=(amount+(2 if previous.endswith('2') else 3 if previous.endswith("'") else 1))%4
        if amount:out.append(face+{1:'',2:'2',3:"'"}[amount])
    return tuple(out)


def run(kind):
    begun=monotonic();g=geometry(kind);grid=g.grid;root=grid.encode(grid.base)
    states=[root];keys=[g.key(root)];parents=[-1];moves=[255];lookup={keys[0]:0};queue=deque([0])
    while queue:
        index=queue.popleft()
        for child,move in grid.children(states[index]):
            key=g.key(child)
            if key in lookup:continue
            lookup[key]=len(states);queue.append(len(states));states.append(child);keys.append(key)
            parents.append(index);moves.append(move)
    print('EXHAUSTED layouts',len(states),'seconds',round(monotonic()-begun,3),flush=True)
    def path(index):
        word=[]
        while parents[index]>=0:word.append(grid.moves[moves[index]]);index=parents[index]
        return tuple(reversed(word))
    degree=len(g.atoms);identity=tuple(range(degree));base=list(identity)
    basis={};group=PermutationGroup([Permutation(identity)]);sieves=None;edges=0
    def prepare():
        nonlocal group,sieves
        group=PermutationGroup([Permutation(list(p)) for p in basis] or [Permutation(identity)])
        group._schreier_sims(base=base)
        valid=[];tables=[]
        for orbit in group.basic_transversals:
            mask=np.zeros(degree,dtype=bool);values=np.zeros((degree,degree),dtype=np.uint8)
            for beta,t in orbit.items():mask[beta]=True;values[beta]=inverse(t.array_form)
            valid.append(mask);tables.append(values)
        sieves=valid,tables
    prepare()
    def first_missing(permutations):
        rows=np.frombuffer(b''.join(permutations),dtype=np.uint8).reshape(-1,degree).copy()
        accepted=np.ones(len(rows),dtype=bool)
        valid,tables=sieves
        for point,mask,table in zip(group.base,valid,tables):
            active=np.flatnonzero(accepted)
            if not len(active):break
            betas=rows[active,point];ok=mask[betas]
            accepted[active[~ok]]=False;active=active[ok];betas=betas[ok]
            if len(active):rows[active]=np.take_along_axis(table[betas],rows[active],axis=1)
        missing=np.flatnonzero(~accepted)
        return int(missing[0]) if len(missing) else None
    def verify_batch(permutations,witnesses):
        while True:
            missing=first_missing(permutations)
            if missing is None:break
            p=permutations[missing];i,move,j=witnesses[missing]
            word=compact(path(i)+(grid.moves[move],)+inverse_word(path(j)))
            replay=grid.base.clone();replay.apply_moves(word)
            actual=[0]*degree;slots={(h,n):a for a,(h,n,c) in enumerate(g.atoms)}
            identities={(h,c):a for a,(h,n,c) in enumerate(g.atoms)}
            for cubie in replay.cubies.values():
                for normal,color in cubie.stickers.items():actual[identities[cubie.home,color]]=slots[cubie.pos,normal]
            assert bytes(actual)==p and g.key(grid.encode(replay))==keys[0]
            basis[p]=word;prepare()
            print('generator',len(basis),'order',group.order(),'seconds',round(monotonic()-begun,3),flush=True)
    batch=[];witnesses=[]
    for i,state in enumerate(states):
        for child,move in grid.children(state):
            j=lookup[g.key(child)];p=g.loop(child,states[j]);edges+=1
            if p==bytes(identity):continue
            batch.append(p);witnesses.append((i,move,j))
            if len(batch)>=2000:verify_batch(batch,witnesses);batch=[];witnesses=[]
    if batch:verify_batch(batch,witnesses)
    print('VERIFIED all graph edges',edges,'basis',len(basis),'order',group.order(),flush=True)
    pool={tuple(p):w for p,w in basis.items()}
    records=build(pool,group.base,group.basic_orbits,group.orbits(),compact,inverse_word,
                  report=lambda *args:print('stabilizer',*args,flush=True))
    # Every exported word is checked again against the actual bandage engine.
    slots={(h,n):a for a,(h,n,c) in enumerate(g.atoms)};identities={(h,c):a for a,(h,n,c) in enumerate(g.atoms)}
    for orbit in records:
        for entry in orbit.values():
            replay=grid.base.clone();replay.apply_moves(entry['word']);actual=[0]*degree
            for cubie in replay.cubies.values():
                for normal,color in cubie.stickers.items():actual[identities[cubie.home,color]]=slots[cubie.pos,normal]
            assert actual==list(entry['permutation']) and g.key(grid.encode(replay))==keys[0]
    order=sorted(range(len(keys)),key=lambda i:keys[i]);remap={old:new for new,old in enumerate(order)}
    width=(len(g.shapes)+7)//8
    blob=(b''.join(keys[i].to_bytes(width,'big') for i in order)
          +b''.join(struct.pack('<I',remap[parents[i]] if parents[i]>=0 else 0xffffffff) for i in order)
          +bytes(moves[i] for i in order))
    header=dict(kind=kind,count=len(states),geometry=grid.fingerprint,root=keys[0],edges=edges,key_bytes=width)
    encoded=json.dumps(header,separators=(',',':')).encode();folder=Path('solver/data')
    name=kind.removesuffix('_cube')
    (folder/(name+'_shapes.bin')).write_bytes(b'BS01'+struct.pack('<I',len(encoded))+encoded+zlib.compress(blob,9))
    table=dict(version=1,kind=kind,geometry=grid.fingerprint,base=group.base,transversals=records,
               order=str(group.order()),exhaustive_layouts=len(states),verified_edges=edges)
    (folder/(name+'_group.bin')).write_bytes(zlib.compress(json.dumps(table,separators=(',',':')).encode(),9))
    print('SAVED seconds',round(monotonic()-begun,3),flush=True)


if __name__=='__main__':
    for kind in sys.argv[1:] or ('burr_cube','ai_cube'):run(kind)
