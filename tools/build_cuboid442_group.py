"""Certified root-layout group for 4x4x2, including deformation loops."""
import json
import sys
import zlib
from collections import deque
from itertools import product
from math import factorial
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from sympy.combinatorics import Permutation,PermutationGroup
from cube.appearance import ROTATIONS,transform_frame
from cube.cuboid import CuboidCube,layout,transform
from solver.cuboid_search import search_model,packed_actions,packed_turn
from tools.weighted_group_builder import build,inverse


def compact(word):
    result=[]
    for a,l,n in word:
        if result and result[-1][:2]==(a,l):n=(result.pop()[2]+n)%4
        if n:result.append((a,l,n))
    return tuple(result)


def inverse_word(word):return tuple((a,l,-n%4) for a,l,n in reversed(word))


def run():
    from solver.cuboid442 import geometry_fingerprint
    started=monotonic();kind='cuboid_442';cube=CuboidCube.solved(kind)
    atoms,transitions,legal,goals,patterns,aliases=search_model(kind)
    cells,boxes,entries,lookup,base=layout(kind);degree=len(entries);identity=tuple(range(degree))
    masks,actions=packed_actions(kind);full=(1<<len(atoms))-1
    shapes=[[ (tuple(sorted(transform(f,p) for p in unit)),tuple(sorted(transform(f,p) for p in product(*boxes[u]))))
              for f in ROTATIONS] for u,unit in enumerate(cells)]
    ids={s:i for i,s in enumerate(sorted({s for row in shapes for s in row}))}
    positions=[[ids[s] for s in row] for row in shapes];bits=[[1<<s for s in row] for row in positions]
    frame_at={f:i for i,f in enumerate(ROTATIONS)};inv=tuple(frame_at[tuple(zip(*f))] for f in ROTATIONS)
    products=tuple(tuple(frame_at[tuple(transform_frame(a,v) for v in b)] for b in ROTATIONS) for a in ROTATIONS)
    homes=tuple(tuple(i for i,(p,n) in enumerate(entries) if p in unit) for unit in cells)
    images=tuple(tuple(tuple(lookup[transform(f,entries[i][0]),transform(f,entries[i][1])] for i in indices)
                       for f in ROTATIONS) for indices in homes)
    def key(state):
        value=0
        for u,v in enumerate(state):value|=bits[u][v-(u%8)*24]
        return value
    def children(state):
        mask=full
        for u,v in enumerate(state):mask&=masks[u][v]
        while mask:
            bit=mask&-mask;mask^=bit;i=bit.bit_length()-1
            child=packed_turn(state,actions[i])
            if child!=state:yield child,i
    def loop(child,representative):
        backwards={positions[u][v-(u%8)*24]:inv[v-(u%8)*24] for u,v in enumerate(representative)}
        result=[0]*degree
        for u,v in enumerate(child):
            pose=v-(u%8)*24;dest=products[backwards[positions[u][pose]]][pose]
            for source,target in zip(homes[u],images[u][dest]):result[source]=target
        return bytes(result)
    root=bytes((u%8)*24+aliases[u][frame_at[cube.frames[u]]] for u in range(len(cells)))
    states=[root];keys=[key(root)];by_key={keys[0]:0};parents=[(-1,-1)];depths=[0];pending=deque([0])
    while pending:
        i=pending.popleft()
        if depths[i]>=4:continue
        for child,move in children(states[i]):
            k=key(child)
            if k in by_key:continue
            by_key[k]=len(states);pending.append(len(states));states.append(child);keys.append(k)
            parents.append((i,move));depths.append(depths[i]+1)
    print('ROOT BALL',len(states),flush=True)
    def path(i):
        word=[]
        while parents[i][0]>=0:
            i,move=parents[i];m=atoms[move];word.append((m.axis,m.layer,m.amount))
        return tuple(reversed(word))
    basis={}
    for child,i in children(root):
        if key(child)==keys[0]:
            m=atoms[i];basis[loop(child,root)]=((m.axis,m.layer,m.amount),)
    group=None;sieves=None
    base_order=sorted(identity,key=lambda i:(-len(homes[base.stickers[i].piece]),i))
    # A restored rigid brick has only eight possible root positions. The
    # two mirror-related edge-brick classes cannot exchange: their bar axis
    # is fixed by the restored shape. Compute these positional orbits rather
    # than treating the sixteen edge bricks as one ordinary-cube orbit.
    root_owner={positions[u][root[u]-(u%8)*24]:u for u in range(len(cells))}
    links=list(range(len(cells)))
    def find(u):
        while links[u]!=u:links[u]=links[links[u]];u=links[u]
        return u
    for u,row in enumerate(positions):
        for shape in row:
            v=root_owner.get(shape)
            if v is not None:links[find(u)]=find(v)
    root_orbits={}
    for u in range(len(cells)):root_orbits.setdefault(find(u),[]).append(u)
    assert sorted(map(len,root_orbits.values()))==[8,8,8,8]
    target=1
    for orbit in root_orbits.values():target*=factorial(len(orbit))
    # On the supporting 4x4, centre parity equals corner parity. In the
    # restored brick layout this is one relation on the four brick orbits.
    target//=2
    def prepare():
        nonlocal group,sieves
        group=PermutationGroup([Permutation(list(p)) for p in basis]);group._schreier_sims(base=base_order)
        valid=[];tables=[]
        for orbit in group.basic_transversals:
            mask=np.zeros(degree,dtype=bool);values=np.zeros((degree,degree),dtype=np.uint8)
            for beta,t in orbit.items():mask[beta]=True;values[beta]=inverse(t.array_form)
            valid.append(mask);tables.append(values)
        sieves=valid,tables
    prepare();print('FIXED ORDER',group.order(),'UPPER',target,flush=True)
    def first_missing(permutations):
        rows=np.frombuffer(b''.join(permutations),dtype=np.uint8).reshape(-1,degree).copy();accepted=np.ones(len(rows),bool)
        for point,mask,table in zip(group.base,*sieves):
            active=np.flatnonzero(accepted)
            if not len(active):break
            betas=rows[active,point];ok=mask[betas];accepted[active[~ok]]=False
            active=active[ok];betas=betas[ok]
            if len(active):rows[active]=np.take_along_axis(table[betas],rows[active],axis=1)
        missing=np.flatnonzero(~accepted)
        return int(missing[0]) if len(missing) else None
    def verify_batch(permutations,witnesses):
        while group.order()!=target:
            missing=first_missing(permutations)
            if missing is None:break
            i,move,j=witnesses[missing];m=atoms[move]
            word=compact(path(i)+((m.axis,m.layer,m.amount),)+inverse_word(path(j)))
            p=permutations[missing];work=CuboidCube(kind,list(identity));work.apply_moves(type(m)(*raw) for raw in word)
            assert bytes(inverse(work.colors))==p
            basis[p]=word;prepare()
            if group.order()>target or target%group.order():raise ValueError('Rigid-brick group exceeds its parity bound')
            print('GENERATOR',len(basis),'ORDER',group.order(),'seconds',round(monotonic()-started,3),flush=True)
    batch=[];witnesses=[]
    for i,state in enumerate(states):
        if group.order()==target:break
        for child,move in children(state):
            j=by_key.get(key(child))
            if j is None:continue
            p=loop(child,states[j])
            if p==bytes(identity):continue
            batch.append(p);witnesses.append((i,move,j))
            if len(batch)>=1000:verify_batch(batch,witnesses);batch=[];witnesses=[]
    if batch:verify_batch(batch,witnesses)
    if group.order()!=target:raise ValueError(('Incomplete root fibre',group.order(),target))
    print('PROVED full parity bound',target,flush=True)
    records=build({tuple(p):w for p,w in basis.items()},group.base,group.basic_orbits,group.orbits(),compact,inverse_word,
                  report=lambda *args:print('stabilizer',*args,flush=True))
    from cube.polyhedral import Move
    verified=0
    for orbit in records:
        for entry in orbit.values():
            work=CuboidCube(kind,list(identity));work.apply_moves(Move(*raw) for raw in entry['word'])
            assert tuple(inverse(work.colors))==tuple(entry['permutation']);verified+=1
    data=dict(version=1,kind=kind,geometry=geometry_fingerprint(),base=group.base,transversals=records,
              order=str(group.order()),parity_bound=str(target),root_orbits=list(root_orbits.values()),verified_transversals=verified,
              goal_colors=[s.face for s in base.stickers])
    out=Path('artifacts/development/cuboid_442-group.bin')
    out.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',out.stat().st_size,'seconds',round(monotonic()-started,3),flush=True)


if __name__=='__main__':run()
