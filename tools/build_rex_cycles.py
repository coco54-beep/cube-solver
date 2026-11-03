"""Discover and verify short staged cycles from actual Rex cut actions."""
import json
from pathlib import Path
import sys
from itertools import permutations
from collections import deque
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle,Move
from solver.polyhedral import apply_word,inverse_word,simplify,piece_orbits


def flip_pair(cube,edge_orbit,native_word=None):
    """Compare two geometric lifts of the same three-edge position cycle."""
    g=cube.geometry
    if native_word is None:
        native=next(m for m in cube.moves() if sum(p in g.layers[m.axis][m.layer] for p in edge_orbit)==3)
        native_word=(native,)
    p=apply_word(g,native_word);a=next(s for h in edge_orbit for s in g.pieces[h] if p[s]!=s)
    root=(a,p[a],p[p[a]])
    def canonical(state):
        rotations=(state,state[1:]+state[:1],state[2:]+state[:2])
        return min(rotations,key=lambda row:tuple(g.stickers[s].piece for s in row))
    root=canonical(root);owner=lambda row:tuple(g.stickers[s].piece for s in row)
    saved={owner(root):(root,())};queue=deque([root]);actions=[]
    for m in cube.moves():
        for amount in (1,2):
            move=Move(m.axis,m.layer,amount);actions.append((move,g.permutation(move)))
    def cycle_action(state):
        result=list(range(len(g.stickers)))
        for a,b in zip(state,state[1:]+state[:1]):
            result[a]=b
            other_a=next(s for s in g.pieces[g.stickers[a].piece] if s!=a)
            other_b=next(s for s in g.pieces[g.stickers[b].piece] if s!=b)
            result[other_a]=other_b
        return tuple(result)
    while queue:
        state=queue.popleft();path=saved[owner(state)][1]
        for move,action in actions:
            child=canonical(tuple(action[s] for s in state));k=owner(child);child_path=path+(move,)
            if k not in saved:saved[k]=(child,child_path);queue.append(child);continue
            before,before_path=saved[k]
            if cycle_action(before)==cycle_action(child):continue
            first=inverse_word(before_path,3)+native_word+before_path
            second=inverse_word(child_path,3)+native_word+child_path
            word=simplify(first+inverse_word(second,3),3);effect=apply_word(g,word)
            flipped=tuple(h for h in edge_orbit if any(effect[s]!=s for s in g.pieces[h]))
            if len(flipped)!=2 or any(g.stickers[effect[s]].piece!=h for h in edge_orbit for s in g.pieces[h]):
                raise ValueError('Rex lift difference is not a two-edge flip')
            print('edge flip',len(word),'moves',flipped,'position triples explored',len(saved),flush=True)
            return dict(word=[(m.axis,m.layer,m.amount) for m in word],base=flipped)
    raise ValueError('No independent Rex edge-flip pair found')


def discover(kind='mf8_bauhinia_minx'):
    cube=PolyhedralPuzzle(kind,3);g=cube.geometry
    identity=np.arange(len(g.stickers));orbits=piece_orbits(cube.puzzle_kind,3)
    slots=[np.array([s for p in orbit for s in g.pieces[p]]) for orbit in orbits]
    first=np.array([p[0] for p in g.pieces]);owner=np.array([s.piece for s in g.stickers])
    best={}
    def consider(p,word):
        disturbed=sum(1<<i for i,s in enumerate(slots) if np.any(p[s]!=s))
        if not disturbed:return
        point=owner[p[first]]
        for i,orbit in enumerate(orbits):
            changed=[p for p in orbit if point[p]!=p]
            if len(changed)!=3:continue
            a=changed[0];b=int(point[a]);c=int(point[b])
            if len({a,b,c})!=3 or int(point[c])!=a:continue
            if np.any(p[p[p[slots[i]]]]!=slots[i]):continue
            record=(i,disturbed&~(1<<i));old=best.get(record)
            if old is not None and len(old[0])<=len(word):continue
            compact=simplify(word,3)
            if old is None or len(compact)<len(old[0]):best[record]=(compact,(a,b,c))
    atoms=[(m,) for m in cube.moves()]
    atoms=[(Move(w[0].axis,0,k),) for w in atoms for k in (1,2)]
    atom_perms=[np.array(apply_word(g,w)) for w in atoms]
    for p,w in zip(atom_perms,atoms):consider(p,w)
    comms={}
    for p,a in zip(atom_perms,atoms):
        pi=np.argsort(p)
        for q,b in zip(atom_perms,atoms):
            action=np.argsort(q)[pi[q[p]]]
            word=simplify(a+b+inverse_word(a,3)+inverse_word(b,3),3)
            if np.any(action!=identity):
                consider(action,word);comms.setdefault(tuple(action),(action,word))
    records=list(comms.values());q=np.stack([p for p,w in records]);qi=np.argsort(q,axis=1)
    for index,(p,a) in enumerate(records):
        if a[0].axis!=0:continue
        actions=np.take_along_axis(qi,np.argsort(p)[q[:,p]],axis=1)
        for action,(ignored,b) in zip(actions,records):
            consider(action,a+b+inverse_word(a,3)+inverse_word(b,3))
        if index%64==0:print('nested',index,len(records),'variants',len(best),flush=True)
    # Two stages can carry the same small centre cycle. Conjugate one so
    # that the centre actions commute while its other support changes, then
    # take their commutator. This removes the shared residual action.
    for word,base in tuple(best.values()):
        p=np.array(apply_word(g,word));pi=np.argsort(p)
        for q,b in tuple(zip(atom_perms,atoms))+tuple(records):
            direct=np.argsort(q)[pi[q[p]]]
            consider(direct,word+b+inverse_word(word,3)+inverse_word(b,3))
            conjugate=np.argsort(q)[p[q]]
            action=np.argsort(conjugate)[pi[conjugate[p]]]
            conjugate_word=b+word+inverse_word(b,3)
            consider(action,word+conjugate_word+inverse_word(word,3)+inverse_word(conjugate_word,3))
    answer=None
    for order in permutations(range(len(orbits))):
        prior=0;macros={}
        for i in order:
            available=[(w,b) for (target,mask),(w,b) in best.items() if target==i and not mask&prior]
            if not available:break
            macros[i]=min(available,key=lambda row:len(row[0]));prior|=1<<i
        else:
            score=sum(len(w)*len(orbits[i]) for i,(w,b) in macros.items())
            if answer is None or score<answer[0]:answer=score,order,macros
    print('best variants',[(i,mask,len(w)) for (i,mask),(w,b) in sorted(best.items())],flush=True)
    if answer is None:raise ValueError('No complete staged cycle order')
    score,order,macros=answer
    print('ORDER',order,'WORDS',[(i,len(w)) for i,(w,b) in macros.items()],flush=True)
    prior=set()
    for i in order:
        word,base=macros[i];action=apply_word(g,word)
        if any(action[s]!=s for s in prior):raise ValueError('Cycle damages a completed stage')
        if any(action[action[action[s]]]!=s for s in slots[i]):raise ValueError('Cycle has extra orientation')
        prior.update(int(s) for s in slots[i])
    return dict(order=order,cycles={str(i):dict(word=[(m.axis,m.layer,m.amount) for m in w],base=b)
                                   for i,(w,b) in macros.items()})


if __name__=='__main__':
    data=discover()
    from solver.lattice_data import geometry_key
    from solver.polyhedral_reduction import Transports
    import zlib
    cube=PolyhedralPuzzle('mf8_bauhinia_minx',3);g=cube.geometry
    orbits=piece_orbits(cube.puzzle_kind,3);certificate={}
    for i in data['order']:
        orbit=orbits[i];base=tuple(data['cycles'][str(i)]['base'])
        transport=Transports(cube,orbit,base)
        while transport._expand():pass
        reachable=int((transport.parents>=0).sum());expected=len(orbit)*(len(orbit)-1)*(len(orbit)-2)//3
        if reachable!=expected:raise ValueError('Rex macro lacks full directed triple coverage')
        certificate[str(i)]=reachable
        print('verified',i,'directed triples',reachable,flush=True)
    data.update(version=1,geometry=geometry_key(g),coverage=certificate,
                edge_flip=flip_pair(cube,orbits[0]))
    path=Path('solver/data/mf8_bauhinia_minx_cycles.bin')
    path.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',path,path.stat().st_size,flush=True)
