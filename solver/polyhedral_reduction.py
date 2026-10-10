"""Pure three-cycle reduction for the movable orbits of high-order minxes."""
from array import array
from collections import deque
from functools import lru_cache
from math import gcd

from cube.polyhedral import PolyhedralPuzzle, Move, dot
from solver.polyhedral import (compose,inverse,apply_word,inverse_word,simplify,
                              piece_orbits,identify,solve_minx)
from solver.nxn_orbits import three_cycles


# A pure three-cycle commutator is eight moves before cancellations.
_SHORT_PRIMITIVE = 8


def _outside_order(perm,target,cycle_order=3):
    seen=set(target)
    result=1
    for i in range(len(perm)):
        if i in seen:
            continue
        j=i
        length=0
        while j not in seen:
            seen.add(j)
            length+=1
            j=perm[j]
        if length>1:
            result=result*length//gcd(result,length)
            if result%cycle_order==0 or result>60:
                return 0
    return result


def primitives(cube,targets,cancel=None,progress=None):
    """Find a cycle whose complete sticker support is one target orbit."""
    g=cube.geometry
    turn_order=g.spec.turn_order
    identity=tuple(range(len(g.stickers)))
    pending=set(targets)
    found={}
    deferred=[]
    transports={}
    target_stickers={i:{s for p in orbit for s in g.pieces[p]}
                     for i,orbit in targets.items()}
    atoms=cube.moves()
    perms={m:g.permutation(m) for m in atoms}
    inv_perms={m:inverse(perms[m]) for m in atoms}
    bp_cache={}
    adjacent=[i for i,a in enumerate(g.spec.axes) if .05<abs(dot(g.spec.axes[0],a))<.8]
    candidates=[(a,b,c,power) for a in atoms if a.axis==0
                for b in atoms if b.axis in adjacent
                for c in atoms if c.axis!=b.axis
                for power in range(1,turn_order)]
    for step,(a,b,c,power) in enumerate(candidates):
        if step%32==0:
            if cancel and cancel():
                raise InterruptedError()
            if progress:
                progress(step,len(candidates))
        bw=(Move(b.axis,b.layer,power),c,Move(b.axis,b.layer,turn_order-power))
        cached=bp_cache.get((b,c,power))
        if cached is None:
            bp=apply_word(g,bw)
            cached=(bp,inverse(bp))
            bp_cache[(b,c,power)]=cached
        bp,invbp=cached
        p=compose(compose(compose(perms[a],bp),inv_perms[a]),invbp)
        point_perm=[g.stickers[p[slots[0]]].piece for slots in g.pieces]
        for index in tuple(pending):
            orbit=targets[index]
            moved=[i for i in orbit if point_perm[i]!=i]
            if len(moved) not in (3,5) or any(point_perm[i] not in moved for i in moved):
                continue
            cycle_order=len(moved)
            order=_outside_order(p,target_stickers[index],cycle_order)
            if not order:
                if cycle_order==3:
                    deferred.append((index,p,(a,)+bw+(a.inverse(turn_order),)+inverse_word(bw,turn_order)))
                continue
            powered=identity
            for _ in range(order):
                powered=compose(powered,p)
            if any(powered[i]!=i for i in range(len(p)) if i not in target_stickers[index]):
                continue
            word=simplify(((a,)+bw+(a.inverse(turn_order),)+inverse_word(bw,turn_order))*order,turn_order)
            if cycle_order==5:
                converted=False
                for atom in atoms:
                    q=perms[atom]
                    conjugate=compose(compose(q,powered),inverse(q))
                    comm=compose(compose(compose(powered,conjugate),inverse(powered)),inverse(conjugate))
                    trip=[i for i in orbit if g.stickers[comm[g.pieces[i][0]]].piece!=i]
                    if len(trip)!=3:
                        continue
                    conjugate_word=(atom,)+word+(atom.inverse(turn_order),)
                    word=simplify(word+conjugate_word+inverse_word(word,turn_order)+
                                  inverse_word(conjugate_word,turn_order),turn_order)
                    powered=comm
                    moved=trip
                    converted=True
                    break
                if not converted:
                    continue
            origin=moved[0]
            second=g.stickers[powered[g.pieces[origin][0]]].piece
            third=g.stickers[powered[g.pieces[second][0]]].piece
            if g.stickers[powered[g.pieces[third][0]]].piece!=origin:
                continue
            current=found.get(index)
            if current is None or len(word)<len(current[0]):
                found[index]=(word,(origin,second,third))
                # A pure three-cycle commutator is about eight moves; keep
                # scanning while any orbit still lacks a compact macro.
                if len(word)<=_SHORT_PRIMITIVE:
                    pending.discard(index)
        if not pending:
            return found
    # Some centre commutators also cycle a shallower centre orbit. Once that
    # orbit has its own pure cycle, cancel its action to isolate the new one.
    pending={index for index in targets if index not in found}
    while pending:
        changed=False
        for index,p,word in deferred:
            if index not in pending:
                continue
            power=1
            seen=set()
            bad=False
            for start in range(len(p)):
                if start in seen:
                    continue
                length=0
                j=start
                while j not in seen:
                    seen.add(j)
                    length+=1
                    j=p[j]
                if length>1 and length%3:
                    power=power*length//gcd(power,length)
                elif length>3:
                    bad=True
            if bad or power%3==0 or power>60:
                continue
            powered=identity
            for _ in range(power):
                powered=compose(powered,p)
            affected={i for i,orbit in targets.items() if i!=index and
                      any(powered[s]!=s for home in orbit for s in g.pieces[home])}
            outside={s for s in range(len(p)) if powered[s]!=s and
                     s not in target_stickers[index]}
            if not affected.issubset(found) or any(
                s not in set().union(*(target_stickers[i] for i in affected)) for s in outside):
                continue
            corrected=list(word*power)
            for other in affected:
                orbit=targets[other]
                indexes={home:i for i,home in enumerate(orbit)}
                destination=[None]*len(orbit)
                for home in orbit:
                    pos=g.stickers[powered[g.pieces[home][0]]].piece
                    destination[indexes[pos]]=indexes[home]
                cycles=three_cycles(destination)
                primitive,base=found[other]
                if other not in transports:
                    transports[other]=Transports(cube,orbit,base,cancel)
                for cycle in cycles:
                    path=transports[other].path(tuple(orbit[j] for j in cycle))
                    correction=inverse_word(path,turn_order)+primitive+path
                    powered=compose(powered,apply_word(g,correction))
                    corrected.extend(correction)
            if any(powered[s]!=s for s in range(len(p)) if s not in target_stickers[index]):
                continue
            moved=[home for home in targets[index]
                   if g.stickers[powered[g.pieces[home][0]]].piece!=home]
            if len(moved)!=3:
                continue
            a=moved[0]
            b=g.stickers[powered[g.pieces[a][0]]].piece
            c=g.stickers[powered[g.pieces[b][0]]].piece
            found[index]=(simplify(corrected,turn_order),(a,b,c))
            pending.remove(index)
            changed=True
            if not pending:
                return found
        if not changed:
            break
    if pending:
        raise ValueError('No independent three-cycle found for these orbits: '+str(sorted(pending)))
    return found


class Transports:
    """Compact predecessor tree on rotation classes of ordered orbit triples.

    A three-cycle (a b c) is the same action as its rotations (b c a) and
    (c a b), so every BFS state is folded to the smallest rotation. That folds
    the search space about threefold; the reconstructed word still lands on a
    rotation of the requested cycle, which realises the same permutation.
    """
    def __init__(self,cube,orbit,base,cancel=None):
        g=cube.geometry
        index={p:i for i,p in enumerate(orbit)}
        self.size=len(orbit)
        identity=tuple(range(self.size))
        maps=[]
        moves=[]
        seen=set()
        for move in cube.moves():
            perm=g.permutation(move)
            orbit_perm=tuple(index[g.stickers[perm[g.pieces[p][0]]].piece] for p in orbit)
            # Moves that fix this orbit, and duplicate actions, add no branches.
            if orbit_perm==identity or orbit_perm in seen:
                continue
            seen.add(orbit_perm)
            maps.append(orbit_perm)
            moves.append(move)
        self.moves=tuple(moves)
        self.maps=tuple(maps)
        size=self.size
        self.size2=size*size
        root=self._canon(*(index[p] for p in base))
        self.parents=array('i',[-1])*(size*size*size)
        self.via=array('h',[-1])*(size*size*size)
        self.parents[root]=root
        self.queue=deque([root])
        self.index=index
        self.cancel=cancel

    def _canon(self,a,b,c):
        size=self.size
        size2=self.size2
        e0=a*size2+b*size+c
        e1=b*size2+c*size+a
        e2=c*size2+a*size+b
        return e0 if e0<=e1 and e0<=e2 else (e1 if e1<e2 else e2)

    def path(self,target):
        index=self.index
        size=self.size
        size2=self.size2
        parents=self.parents
        via=self.via
        maps=self.maps
        moves=self.moves
        queue=self.queue
        cancel=self.cancel
        code=self._canon(*(index[p] for p in target))
        steps=0
        while parents[code]<0:
            if not queue:
                raise ValueError('The requested three-cycle is not in this orbit')
            parent=queue.popleft()
            a,b=divmod(parent,size2)
            b,c=divmod(b,size)
            for j,perm in enumerate(maps):
                pa=perm[a]; pb=perm[b]; pc=perm[c]
                e0=pa*size2+pb*size+pc
                e1=pb*size2+pc*size+pa
                e2=pc*size2+pa*size+pb
                nxt=e0 if e0<=e1 and e0<=e2 else (e1 if e1<e2 else e2)
                if parents[nxt]<0:
                    parents[nxt]=parent
                    via[nxt]=j
                    queue.append(nxt)
            steps+=1
            if steps%1024==0 and cancel and cancel():
                raise InterruptedError()
        word=[]
        append=word.append
        while parents[code]!=code:
            append(moves[via[code]])
            code=parents[code]
        return tuple(reversed(word))


def solve_high_minx(cube,cancel=None,progress=None):
    work=cube.entered()
    g=work.geometry
    core=PolyhedralPuzzle('megaminx',3 if cube.n%2 else 2)
    core_sets={tuple(sorted(core.geometry.stickers[s].face for s in p)):p
               for p in core.geometry.pieces if len(p)>1}
    orbits=piece_orbits(cube.puzzle_kind,cube.n)
    core_orbits={i for i,o in enumerate(orbits) if len(g.pieces[o[0]])==3 or
                 (len(o)==30 and len(g.pieces[o[0]])==2)}
    for index in core_orbits:
        for p in orbits[index]:
            slots=g.pieces[p]
            colors=tuple(sorted(g.stickers[s].face for s in slots))
            core_slots=core_sets[colors]
            by_face={core.geometry.stickers[s].face:s for s in core_slots}
            for s in slots:
                core.colors[by_face[g.stickers[s].face]]=work.colors[s]
    solution=list(solve_minx(core,cancel))
    for move in solution:
        work.apply_move(move)
    targets={i:o for i,o in enumerate(orbits) if len(o)>1 and i not in core_orbits}
    macros=primitives(work,targets,cancel)
    for stage,(index,orbit) in enumerate(targets.items()):
        if cancel and cancel():
            raise InterruptedError()
        if progress:
            progress(stage,len(targets))
        state=identify(work)
        indexes={p:i for i,p in enumerate(orbit)}
        destination=[None]*len(orbit)
        for home in orbit:
            position=g.stickers[state[g.pieces[home][0]]].piece
            destination[indexes[position]]=indexes[home]
        cycles=three_cycles(destination)
        if not cycles:
            continue
        primitive,base=macros[index]
        transports=Transports(work,orbit,base,cancel)
        for cycle in cycles:
            target=tuple(orbit[i] for i in cycle)
            path=transports.path(target)
            word=inverse_word(path,5)+primitive+path
            for move in word:
                work.apply_move(move)
            solution.extend(word)
    if not work.is_solved():
        raise ValueError('Higher-order reduction replay failed')
    return simplify(solution,5)


def solve_tetrahedral(cube,cancel=None,progress=None):
    """Solve the small orientation core, then the independent added orbits."""
    from solver.polyhedral_search import solve_core
    work=cube.entered()
    g=work.geometry
    identify(work)
    solution=list(solve_core(work,cancel,progress))
    for move in solution:
        work.apply_move(move)
    if cube.puzzle_kind=='pyraminx' and cube.n>=3:
        for axis,layers in enumerate(g.layers):
            if len(layers[0])!=1:
                continue
            slots=g.pieces[layers[0][0]]
            for amount in range(g.spec.turn_order):
                move=Move(axis,0,amount)
                perm=g.permutation(move)
                if all(work.colors[s]==g.stickers[perm[s]].face for s in slots):
                    if amount:
                        work.apply_move(move)
                        solution.append(move)
                    break
            else:
                raise ValueError('The entered core has an impossible orientation')
    orbits=piece_orbits(cube.puzzle_kind,cube.n)
    targets={i:o for i,o in enumerate(orbits) if len(o)>6 and len(g.pieces[o[0]])<3}
    if targets:
        macros=primitives(work,targets,cancel)
        for stage,(index,orbit) in enumerate(targets.items()):
            if progress:
                progress(stage,len(targets))
            state=identify(work)
            indexes={p:i for i,p in enumerate(orbit)}
            destination=[None]*len(orbit)
            for home in orbit:
                pos=g.stickers[state[g.pieces[home][0]]].piece
                destination[indexes[pos]]=indexes[home]
            primitive,base=macros[index]
            transports=Transports(work,orbit,base,cancel)
            for cycle in three_cycles(destination):
                path=transports.path(tuple(orbit[i] for i in cycle))
                word=inverse_word(path,g.spec.turn_order)+primitive+path
                for move in word:
                    work.apply_move(move)
                solution.extend(word)
    if not work.is_solved():
        raise ValueError('Polyhedral reduction replay failed')
    return simplify(solution,g.spec.turn_order)
