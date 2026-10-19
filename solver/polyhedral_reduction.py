"""Pure three-cycle reduction for the movable orbits of high-order minxes."""
from array import array
from collections import OrderedDict, deque
from functools import lru_cache
from math import gcd
import random
from time import monotonic

import numpy as np

from cube.polyhedral import PolyhedralPuzzle, Move, dot
from solver.polyhedral import (compose,inverse,apply_word,inverse_word,simplify,
                              piece_orbits,identify,solve_minx)
from solver.nxn_orbits import three_cycles


# A pure three-cycle commutator is eight moves before cancellations.
_SHORT_PRIMITIVE = 8

# Optional per-orbit trace used by the benchmarks; disabled by default.
_STAGE_TRACE = None


def begin_stage_trace():
    global _STAGE_TRACE
    _STAGE_TRACE = []
    return _STAGE_TRACE


def end_stage_trace():
    global _STAGE_TRACE
    log = _STAGE_TRACE
    _STAGE_TRACE = None
    return log


def _trace_orbit(orbit, word):
    if _STAGE_TRACE is not None:
        _STAGE_TRACE.append({"orbit": len(orbit), "moves": len(word)})


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


def _return_order(perm,must_return,cycle_order=3):
    """Smallest exponent that fixes every sticker in ``must_return``.

    The complement of ``must_return`` may move freely, so unlike
    ``_outside_order`` only the cycles touching guarded stickers contribute.
    Returns zero when no such exponent can yield the requested cycle length.
    """
    seen=set()
    result=1
    for start in must_return:
        if start in seen:
            continue
        j=start
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


def primitives(cube,targets,cancel=None,progress=None,anchor_axis=0,use_prepared=True,
               deep=False,protected=None):
    """Find a cycle whose complete sticker support is one target orbit.

    ``deep`` also tries two-move outer commutator words. It is used by the
    offline asset builders where extra search time is free; solving keeps the
    single-move search for responsiveness.

    ``protected`` optionally maps each target index to the stickers that the
    macro must leave fixed. Piece orbits are invariant under every legal turn,
    so a macro that fixes the stickers of already-solved orbits stays valid
    under any conjugate: ``g**-1 P g`` fixes those orbits because ``g`` merely
    permutes them. This lets later stages tolerate macros that disturb the
    still-unsolved orbits, which are much shorter than fully isolated cycles.
    When omitted, a macro must fix every sticker outside its own orbit.
    """
    if cancel and cancel():
        raise InterruptedError()
    if use_prepared:
        if cube.puzzle_kind in ('dino_skewb','dayan_dino_skewb'):
            from solver.dino_skewb import prepared_cycles
            prepared=prepared_cycles(cube,targets)
        elif cube.puzzle_kind in ('mosaic','tins'):
            from solver.mosaic import prepared_cycles
            prepared=prepared_cycles(cube,targets)
        elif cube.puzzle_kind=='super_ivy':
            from solver.super_ivy import prepared_cycles
            prepared=prepared_cycles(cube,targets)
        elif cube.puzzle_kind=='fto':
            from solver.fto import prepared_cycles
            prepared=prepared_cycles(cube,targets)
        else:
            from solver.lattice_data import primitives_for
            prepared=primitives_for(cube,targets)
        if prepared is not None:
            return prepared
    g=cube.geometry
    turn_order=g.spec.turn_order
    identity=tuple(range(len(g.stickers)))
    npices=len(g.pieces)
    pending=set(targets)
    orbit_arrays={i: np.asarray(targets[i],dtype=np.int64) for i in targets}
    first_pieces=np.asarray([g.pieces[i][0] for i in range(npices)],dtype=np.int64)
    sticker_piece=np.asarray([g.stickers[s].piece for s in range(len(g.stickers))],dtype=np.int64)
    _ap_cache={}

    def _atom_piece(m):
        a=_ap_cache.get(m)
        if a is None:
            pn=np.asarray(g.permutation(m),dtype=np.int64)
            a=sticker_piece[pn[first_pieces]]
            _ap_cache[m]=a
        return a

    def _word_piece(word):
        arr=None
        for m in word:
            pa=_atom_piece(m)
            arr=pa if arr is None else pa[arr]
        return arr

    def _inv_np(a):
        inv=np.empty(len(a),dtype=np.int64)
        inv[a]=np.arange(len(a),dtype=np.int64)
        return inv
    found={}
    deferred=[]
    transports={}
    target_stickers={i:{s for p in orbit for s in g.pieces[p]}
                     for i,orbit in targets.items()}
    custom=protected is not None
    if custom:
        fixed={i:set(protected.get(i,())) for i in targets}
    else:
        all_stickers=set(range(len(g.stickers)))
        fixed={i:all_stickers-target_stickers[i] for i in targets}
    atoms=cube.moves()
    perms={m:g.permutation(m) for m in atoms}
    inv_perms={m:inverse(perms[m]) for m in atoms}
    # A native generator that is already a pure three-cycle on a target orbit
    # (e.g. a Dino Cube corner turn acting on its edge orbit) is the shortest
    # possible primitive: one move instead of an eight-move commutator.
    atom_point={m:[g.stickers[perms[m][slots[0]]].piece for slots in g.pieces]
                for m in atoms}
    for index in tuple(pending):
        orbit=targets[index]
        for m in atoms:
            point=atom_point[m]
            moved=[i for i in orbit if point[i]!=i]
            if len(moved)!=3 or any(point[i] not in moved for i in moved):
                continue
            if any(perms[m][s]!=s for s in fixed[index]):
                continue
            origin=moved[0]
            second=point[origin]
            third=point[second]
            if point[third]!=origin:
                continue
            found[index]=((m,),(origin,second,third))
            pending.discard(index)
            break
    if not pending:
        return found
    bp_cache=OrderedDict()
    # A record can hold both forward/inverse piece arrays and full sticker
    # permutations. Thousands of inner words otherwise retain hundreds of MB.
    bp_limit=max(1,min(128,8*1024*1024//max(1,16*(npices+len(g.stickers)))))
    # Two centre families can belong to opposite sets of faces. Searching with
    # one face as the outer commutator turn misses its opposite family, so the
    # antipode of the anchor is included for FTO and for the offline deep scan.
    anchors={anchor_axis}
    if cube.puzzle_kind=='fto' or deep:
        anchors.update(i for i,axis in enumerate(g.spec.axes)
                       if dot(g.spec.axes[anchor_axis],axis)<-.99)
    if cube.puzzle_kind=='football':
        # Pentagon and hexagon turns have different orders. Centre cycles
        # in one family cannot all be discovered with the other's anchor.
        anchors.update((0,12))
    elif cube.puzzle_kind in ('blossom', 'petal_icosahedron', 'petal_icosahedron_nocentre','petal_tetrahedron','petal_tetrahedron_nocentre'):
        # Each edge turn reaches only two of the six ten-petal orbits.
        anchors.update(range(len(g.spec.axes)))
    adjacent={i:{j for j,axis in enumerate(g.spec.axes)
                 if .05<abs(dot(g.spec.axes[i],axis))<.8}
              for i in range(len(g.spec.axes))}
    # Outer commutator words. Length one is the original coverage; length two
    # reaches centre orbits (e.g. War Drum drumsides) whose shortest isolating
    # commutator needs an outer pair on antipodal axes.
    outers=[(a,) for a in atoms if a.axis in anchors]
    if deep:
        outers.extend((a1,a2) for a1 in atoms if a1.axis in anchors for a2 in atoms)
    outer_cache={}
    # Inner commutator words. Length one is the plain commutator [a,b], which
    # isolates some orbits (e.g. a deep centre band) that no conjugated
    # three-move inner word reaches in eight moves. Length two and the
    # conjugated three-move word keep the original coverage.
    def candidates():
        for outer in outers:
            last_axis=outer[-1].axis
            for b in atoms:
                if b.axis not in adjacent[last_axis]:
                    continue
                yield outer,(b,)
                for c in atoms:
                    # Same-axis inner pairs are needed by deep centre bands.
                    yield outer,(b,c)
                    if c.axis==b.axis:
                        continue
                    for power in range(1,g.spec.order(b.axis)):
                        amount=power*g.spec.step(b.axis)
                        yield outer,(Move(b.axis,b.layer,amount),c,
                                     Move(b.axis,b.layer,turn_order-amount))
    candidate_count=sum(1+len(atoms)+sum(c.axis!=b.axis for c in atoms)*(g.spec.order(b.axis)-1)
                        for outer in outers for b in atoms if b.axis in adjacent[outer[-1].axis])
    for step,(outer,bw) in enumerate(candidates()):
        if step%32==0:
            if cancel and cancel():
                raise InterruptedError()
            if progress:
                progress(step,candidate_count)
        orec=outer_cache.get(outer)
        if orec is None:
            opp_np=_word_piece(outer)
            orec=[opp_np,_inv_np(opp_np),None,None]
            outer_cache[outer]=orec
        opp_np,invopp_np,op,invop=orec
        brec=bp_cache.get(bw)
        if brec is None:
            bpp_np=_word_piece(bw)
            brec=[bpp_np,_inv_np(bpp_np),None,None]
            if len(bp_cache)>=bp_limit:
                bp_cache.popitem(last=False)
            bp_cache[bw]=brec
        else:
            bp_cache.move_to_end(bw)
        bpp_np,invbpp_np,bp,invbp=brec
        # Screen with the cheap piece-level commutator first; the full sticker
        # word is only built for candidates that actually cycle a target orbit.
        if pending:
            pp_np=invbpp_np[invopp_np[bpp_np[opp_np]]]
            hit=False
            for index in pending:
                oarr=orbit_arrays[index]
                imgs=pp_np[oarr]
                mask=imgs!=oarr
                cnt=int(mask.sum())
                if cnt not in (3,5):
                    continue
                if np.array_equal(np.sort(imgs[mask]),np.sort(oarr[mask])):
                    hit=True
                    break
            if not hit:
                continue
            point_perm=tuple(int(x) for x in pp_np)
        if orec[2] is None:
            orec[2]=apply_word(g,outer)
            orec[3]=inverse(orec[2])
        op,invop=orec[2],orec[3]
        if brec[2] is None:
            brec[2]=apply_word(g,bw)
            brec[3]=inverse(brec[2])
        bp,invbp=brec[2],brec[3]
        p=compose(compose(compose(op,bp),invop),invbp)
        packed=None
        for index in tuple(pending):
            orbit=targets[index]
            moved=[i for i in orbit if point_perm[i]!=i]
            if len(moved) not in (3,5) or any(point_perm[i] not in moved for i in moved):
                continue
            cycle_order=len(moved)
            order=_return_order(p,fixed[index],cycle_order)
            macro=outer+bw+inverse_word(outer,turn_order)+inverse_word(bw,turn_order)
            if not order:
                if cycle_order==3 and not custom:
                    # Deferred full permutations dominated mobile RAM: each
                    # tuple also kept thousands of boxed inverse indices alive.
                    # A compact array preserves every candidate and its order.
                    if packed is None:
                        packed=array('H' if len(p)<=65536 else 'I',p)
                    deferred.append((index,packed,macro))
                continue
            powered=identity
            for _ in range(order):
                powered=compose(powered,p)
            if any(powered[i]!=i for i in fixed[index]):
                continue
            word=simplify(macro*order,turn_order)
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
                # scanning while any orbit still lacks a compact macro. The
                # offline deep scan never stops early so a later, shorter
                # macro (e.g. a four-move commutator) can still be picked up.
                if len(word)<=_SHORT_PRIMITIVE and not deep:
                    pending.discard(index)
        if not pending:
            return found
    # Some centre commutators also cycle a shallower centre orbit. Once that
    # orbit has its own pure cycle, cancel its action to isolate the new one.
    # A deep search can find a direct but longer macro first, so re-check any
    # orbit whose best is still longer than a compact commutator. Runtime
    # solving keeps the original, cheaper pass.
    if deep:
        pending={index for index in targets if index not in found
                 or len(found[index][0])>_SHORT_PRIMITIVE}
    else:
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
            if not affected.issubset(found):
                continue
            allowed=set().union(*(target_stickers[i] for i in affected))
            if not outside.issubset(allowed):
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
                    # A predecessor tree scales cubically with orbit size.
                    # Keep only two trees while discovering centre macros,
                    # rather than one for every high-order centre orbit.
                    if len(transports)>=2:
                        transports.pop(next(iter(transports)))
                    transports[other]=Transports(cube,orbit,base,cancel)
                for cycle in cycles:
                    path=transports[other].path(tuple(orbit[j] for j in cycle))
                    correction=inverse_word(path,turn_order)+primitive+path
                    powered=compose(powered,apply_word(g,correction))
                    corrected.extend(correction)
            if any(powered[s]!=s for s in fixed[index]):
                continue
            moved=[home for home in targets[index]
                   if g.stickers[powered[g.pieces[home][0]]].piece!=home]
            if len(moved)!=3:
                continue
            a=moved[0]
            b=g.stickers[powered[g.pieces[a][0]]].piece
            c=g.stickers[powered[g.pieces[b][0]]].piece
            candidate=simplify(corrected,turn_order)
            if index not in found or len(candidate)<len(found[index][0]):
                found[index]=(candidate,(a,b,c))
            pending.discard(index)
            changed=True
            if not pending:
                return found
        if not changed:
            break
    missing=[index for index in pending if index not in found]
    if missing:
        raise ValueError('No independent three-cycle found for these orbits: '+str(sorted(missing)))
    return found


class Transports:
    """Compact predecessor tree on rotation classes of ordered orbit triples.

    A three-cycle (a b c) is the same action as its rotations (b c a) and
    (c a b), so every BFS state is folded to the smallest rotation. That folds
    the search space about threefold; the reconstructed word still lands on a
    rotation of the requested cycle, which realises the same permutation.
    """
    def __init__(self,cube,orbit,base,cancel=None,both_directions=False):
        g=cube.geometry
        index={p:i for i,p in enumerate(orbit)}
        self.size=len(orbit)
        identity=tuple(range(self.size))
        maps=[]
        moves=[]
        seen=set()
        for atom in cube.moves():
            # Every legal power is one playback step, including inverse turns.
            # Searching only positive turns makes e.g. a -72 degree setup
            # take four steps instead of one.
            for power in range(1,g.spec.order(atom.axis)):
                move=Move(atom.axis,atom.layer,power*g.spec.step(atom.axis))
                perm=g.permutation(move)
                orbit_perm=tuple(index[g.stickers[perm[g.pieces[p][0]]].piece] for p in orbit)
                if orbit_perm==identity or orbit_perm in seen:
                    continue
                seen.add(orbit_perm)
                maps.append(orbit_perm)
                moves.append(move)
        self.moves=tuple(moves)
        self.size2=self.size*self.size
        a,b,c=(index[p] for p in base)
        self.roots={self._canon(a,b,c):False}
        if both_directions:
            self.roots[self._canon(a,c,b)]=True
        self.index=index
        self.cancel=cancel
        self.order=g.spec.turn_order
        size=self.size
        total=size*size*size
        self.parents=np.full(total,-1,dtype=np.int32)
        self.via=np.full(total,-1,dtype=np.int16)
        for root in self.roots:
            self.parents[root]=root
        self._maps_np=np.asarray(maps,dtype=np.int64)
        self._frontier=np.asarray(list(self.roots),dtype=np.int64)

    def _expand(self):
        """Expand one BFS layer over rotation-folded triples (vectorised)."""
        frontier=self._frontier
        if frontier.size==0:
            return False
        size=self.size
        size2=self.size2
        parents=self.parents
        via=self.via
        a=frontier//size2
        b=(frontier//size)%size
        c=frontier%size
        chunks=[]
        for j,perm in enumerate(self._maps_np):
            if self.cancel is not None and self.cancel():
                raise InterruptedError()
            pa=perm[a]; pb=perm[b]; pc=perm[c]
            e0=pa*size2+pb*size+pc
            e1=pb*size2+pc*size+pa
            e2=pc*size2+pa*size+pb
            nxt=np.minimum(np.minimum(e0,e1),e2)
            mask=parents[nxt]<0
            if mask.any():
                dst=nxt[mask]
                parents[dst]=frontier[mask]
                via[dst]=j
                chunks.append(dst)
        self._frontier=(np.unique(np.concatenate(chunks)) if chunks
                        else np.empty(0,dtype=np.int64))
        return True

    def _canon(self,a,b,c):
        size=self.size
        size2=self.size2
        e0=a*size2+b*size+c
        e1=b*size2+c*size+a
        e2=c*size2+a*size+b
        return e0 if e0<=e1 and e0<=e2 else (e1 if e1<e2 else e2)

    def _transport(self,target,deadline=None):
        index=self.index
        parents=self.parents
        code=self._canon(*(index[p] for p in target))
        layers=0
        while parents[code]<0:
            if self.cancel is not None and self.cancel():
                raise InterruptedError()
            if not self._expand():
                raise ValueError('The requested three-cycle is not in this orbit')
            layers+=1
            if self.cancel is not None and layers%16==0 and self.cancel():
                raise InterruptedError()
            if deadline is not None and layers%4==0 and monotonic()>=deadline:
                raise TimeoutError('Optional transport search budget reached')
        via=self.via
        moves=self.moves
        word=[]
        append=word.append
        while parents[code]!=code:
            append(moves[via[code]])
            code=parents[code]
        return tuple(reversed(word)),self.roots[code]

    def path(self,target):
        """Forward-only setup, retained for offline formula builders."""
        if len(self.roots)>1:
            raise ValueError('Use conjugate() when both cycle directions are enabled')
        return self._transport(target)[0]

    def conjugate(self,target,primitive,deadline=None,simplify_result=True):
        """Choose a shortest setup to either orientation of the base cycle.

        ``simplify_result`` can be disabled by callers that simplify the whole
        concatenated plan once; the concatenation is equivalent and avoids a
        per-cycle simplify pass.
        """
        path,reverse=self._transport(target,deadline)
        order=self.order
        macro=inverse_word(primitive,order) if reverse else primitive
        word=inverse_word(path,order)+macro+path
        return simplify(word,order) if simplify_result else word


def joined_length(prefix,suffix,order):
    """Exact simplified join length for two already simplified move words.

    Only the touching axis blocks can change. Fully cancelled blocks expose
    the next boundary; untouched prefixes need no copying or rescanning.
    """
    left=len(prefix)
    right=0
    while left and right<len(suffix) and prefix[left-1].axis==suffix[right].axis:
        axis=prefix[left-1].axis
        layers={}
        while left and prefix[left-1].axis==axis:
            left-=1
            move=prefix[left]
            layers[move.layer]=(layers.get(move.layer,0)+move.amount)%order
        while right<len(suffix) and suffix[right].axis==axis:
            move=suffix[right]
            layers[move.layer]=(layers.get(move.layer,0)+move.amount)%order
            right+=1
        count=sum(bool(amount) for amount in layers.values())
        if count:
            return left+count+len(suffix)-right
    return left+len(suffix)-right


def orbit_word(transports,orbit,destination,primitive,prefix=(),alternatives=True,
               search_budget=0.08):
    """Compare a few equivalent decompositions, keeping the original as fallback.

    Relabel before splitting into three-cycles, then map back to actual pieces.
    This changes pivots and processing order without changing the requested
    position permutation. Alternative plans are used for single-colour pieces;
    their labels have no additional sticker-orientation constraints.
    """
    size=len(orbit)
    order=transports.order
    cancel=transports.cancel

    def plan(labels,deadline=None,reverse=False):
        ids={old:new for new,old in enumerate(labels)}
        permutation=[ids[destination[old]] for old in labels]
        if reverse:
            permutation=inverse(permutation)
        word=[]
        for cycle in three_cycles(permutation):
            if cancel and cancel():
                raise InterruptedError()
            if deadline is not None and monotonic()>=deadline:
                raise TimeoutError('Optional orbit planning budget reached')
            target=tuple(orbit[labels[i]] for i in cycle)
            word.extend(transports.conjugate(target,primitive,deadline,
                                             simplify_result=False))
        if reverse:
            word=inverse_word(word,order)
        return simplify(word,order)

    labels=tuple(range(size))
    best=plan(labels)
    if not alternatives or not best:
        return best
    prefix=simplify(prefix,order)
    best_cost=joined_length(prefix,best,order)
    deadline=monotonic()+max(0.0,search_budget)
    variants=(tuple(reversed(labels)),labels[size//3:]+labels[:size//3],
              labels[2*size//3:]+labels[:2*size//3])
    seen={labels}
    current=labels
    current_cost=best_cost
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        try:
            candidate=plan(variant,deadline)
        except TimeoutError:
            break
        cost=joined_length(prefix,candidate,order)
        if cost<best_cost:
            best,best_cost=candidate,cost
        if cost<current_cost:
            current,current_cost=variant,cost

    # Decomposing the inverse permutation and then reversing the whole word
    # gives the same target action with different pivot/setup cancellations.
    # Compare within the existing time budget and keep only an improvement.
    for variant in (labels,current):
        try:
            candidate=plan(variant,deadline,reverse=True)
        except TimeoutError:
            break
        cost=joined_length(prefix,candidate,order)
        if cost<best_cost:
            best,best_cost=candidate,cost

    # A different relabelling changes how the same permutation is split into
    # three-cycles. Search nearby relabellings so adjacent conjugates can
    # cancel or combine after move simplification. This matters most for the
    # high-order Skewb singleton-centre orbits, where each orbit needs several
    # long setup conjugates. The fixed seed keeps proposal order stable;
    # a wall-clock budget can change how many proposals are evaluated.
    seed=0
    for i,value in enumerate(destination):
        seed=(seed*131+int(value)+i*17)&0xffffffff
    rng=random.Random(seed)
    while monotonic()<deadline:
        changed=list(current)
        # Small relabelling moves explore nearby decompositions; occasional
        # full shuffles escape a local minimum.
        if rng.random()<0.12:
            rng.shuffle(changed)
        else:
            for _ in range(1+(rng.random()<0.25)):
                a,b=rng.sample(range(size),2)
                changed[a],changed[b]=changed[b],changed[a]
        variant=tuple(changed)
        if variant in seen:
            continue
        seen.add(variant)
        try:
            candidate=plan(variant,deadline)
        except TimeoutError:
            break
        cost=joined_length(prefix,candidate,order)
        if cost<best_cost:
            best,best_cost=candidate,cost
        # A modest annealing chance prevents the search from stopping at the
        # first local minimum while preserving a strict best-so-far result.
        if cost<=current_cost or rng.random()<0.08:
            current,current_cost=variant,cost
    _trace_orbit(orbit,best)
    return best


def _macro_cost(macros):
    """Total move count of a mapping index -> (word, base)."""
    return sum(len(word) for word,_ in macros.values())


def _beam_probe(cube,cancel=None):
    """Run the native-ring beam once and report unsolved stickers vs movable set.

    The beam is cheap (well under a second) and leaves almost nothing behind on
    shallow states, while deep scrambles leave most of the movable pieces
    untouched. That gap makes it a reliable depth probe.
    """
    from solver.high_minx_reduction import native_beam, _BEAM_WIDTH
    work=cube.entered()
    g=work.geometry
    orbits=piece_orbits(cube.puzzle_kind,cube.n)
    positions=[p for o in orbits if len(o)>1 for p in o]
    if not positions:
        return work,(),0,0
    m=len(positions)
    width=_BEAM_WIDTH if m<=900 else max(24,49152//m)
    word=native_beam(work,positions,cancel,None,width=width)
    unsolved=sum(1 for i,s in enumerate(g.stickers) if work.colors[i]!=s.face)
    return work,tuple(word),unsolved,m


def _beam_remaining(cube,cancel=None):
    """Compatibility for benchmark callers that only need depth statistics."""
    _,_,unsolved,movable=_beam_probe(cube,cancel)
    return unsolved,movable


def solve_high_minx(cube,cancel=None,progress=None):
    """Choose the pipeline that suits the state depth.

    The native-ring reduction's beam search is excellent on shallow states
    (a twelve-move scramble of order six becomes 39 moves), while the
    three-cycle pipeline is two to five times faster and shorter on deep
    scrambles. A cheap beam probe distinguishes the two cases without running
    the expensive reduction on every state.
    """
    from solver.high_minx_reduction import solve_reduced
    if cube.n<=8:
        try:
            work,beam_word,unsolved,movable=_beam_probe(cube,cancel)
        except (InterruptedError,MemoryError):
            raise
        except Exception:
            unsolved=None
        if unsolved is not None and unsolved<=max(24,movable//4):
            return solve_reduced(cube,cancel,progress,_beam=(work,beam_word))
        # The deep-state pipeline does not use the probe's working copy.
        work=None
        beam_word=()
    try:
        return _solve_high_minx_legacy(cube,cancel,progress)
    except (InterruptedError,MemoryError):
        raise
    except Exception:
        return solve_reduced(cube,cancel,progress)


def _solve_high_minx_legacy(cube,cancel=None,progress=None):
    work=cube.entered()
    g=work.geometry
    if cancel and cancel():
        raise InterruptedError()
    # Validate every orbit before solving the projected core or constructing
    # expensive centre macros. Missing high-order centres are absent from the
    # projection and otherwise would only be noticed after that work finishes.
    identify(work)
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
    solution=list(solve_minx(core,cancel,optimize=False))
    for move in solution:
        work.apply_move(move)
    targets={i:o for i,o in enumerate(orbits) if len(o)>1 and i not in core_orbits}
    # High-order minx has many large independent piece orbits. Give the
    # equivalent three-cycle planner more time than the generic default, but
    # cap the combined search so 11th/13th-order puzzles stay responsive.
    orbit_search_budget=min(0.45,1.0/max(1,len(targets)))
    from solver.minx_plans import core_orbit_plan
    prepared=core_orbit_plan(work,targets)
    baseline=prepared[0] if prepared is not None else primitives(work,targets,cancel)
    # Odd orders have orbits whose isolating commutator is long. Solving the
    # hardest orbit first and protecting the orbits already solved lets those
    # macros be built with fewer fixed stickers, so they become short. The
    # staged plan is only adopted when it lowers the total macro cost, keeping
    # the cheaper disjoint plan for even orders where every macro is already
    # minimal. ``primitives`` protects exact sticker sets; because piece orbits
    # are invariant under every turn, a macro that fixes a solved orbit stays
    # valid under any setup, so a solved orbit is never disturbed again.
    staged=None
    if prepared is not None and prepared[2]:
        staged=baseline
        order=prepared[1]
    if prepared is None and any(len(baseline[i][0])>_SHORT_PRIMITIVE for i in baseline):
        order=sorted(targets,key=lambda i:-len(baseline[i][0]))
        guarded=set()
        for index in core_orbits:
            guarded.update(s for p in orbits[index] for s in g.pieces[p])
        protected={}
        for index in order:
            protected[index]=set(guarded)
            guarded.update(s for p in targets[index] for s in g.pieces[p])
        try:
            staged=primitives(work,targets,cancel,protected=protected)
        except ValueError:
            staged=None
    if staged is not None and (prepared is not None or _macro_cost(staged)<_macro_cost(baseline)):
        for stage,index in enumerate(order):
            if cancel and cancel():
                raise InterruptedError()
            if progress:
                progress(stage,len(order))
            orbit=targets[index]
            primitive,base=staged[index]
            state=identify(work,only=(index,))
            indexes={p:i for i,p in enumerate(orbit)}
            destination=[None]*len(orbit)
            for home in orbit:
                position=g.stickers[state[g.pieces[home][0]]].piece
                destination[indexes[position]]=indexes[home]
            if not three_cycles(destination):
                continue
            transports=Transports(work,orbit,base,cancel,both_directions=True)
            word=orbit_word(transports,orbit,destination,primitive,solution,
                            alternatives=len(g.pieces[orbit[0]])==1,
                            search_budget=orbit_search_budget)
            for move in word:
                work.apply_move(move)
            solution.extend(word)
        if not work.is_solved():
            raise ValueError('Higher-order reduction replay failed')
        return simplify(solution,5)
    macros=baseline
    state=identify(work)
    plans=[]
    for stage,(index,orbit) in enumerate(targets.items()):
        if cancel and cancel():
            raise InterruptedError()
        if progress:
            progress(stage,len(targets))
        indexes={p:i for i,p in enumerate(orbit)}
        destination=[None]*len(orbit)
        for home in orbit:
            position=g.stickers[state[g.pieces[home][0]]].piece
            destination[indexes[position]]=indexes[home]
        cycles=three_cycles(destination)
        if not cycles:
            continue
        primitive,base=macros[index]
        transports=Transports(work,orbit,base,cancel,both_directions=True)
        word=orbit_word(transports,orbit,destination,primitive,solution,
                        alternatives=len(g.pieces[orbit[0]])==1,
                        search_budget=orbit_search_budget)
        plans.append((index,word))

    # These macros act on disjoint piece orbits, so their order is free.
    # Greedily choose the next orbit that makes the simplified accumulated
    # sequence shortest; this captures cancellations across orbit boundaries.
    pending=list(plans)
    ordered=[]
    prefix=simplify(solution,5)
    while pending:
        if cancel and cancel():
            raise InterruptedError()
        choice=min(range(len(pending)),
                   key=lambda i:joined_length(prefix,pending[i][1],5))
        _,word=pending.pop(choice)
        ordered.append(word)
        prefix=simplify(prefix+word,5)
    for word in ordered:
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
    if cube.puzzle_kind == 'pyraminx' and cube.n == 5:
        from solver.pyraminx_high import short_solution
        short = short_solution(work, cancel)
        if short is not None:
            return short
    if cube.puzzle_kind=='skewb' and cube.n in (5,7):
        from solver.skewb import solve_high_order_core
        solution=list(solve_high_order_core(work,cancel,progress))
    elif cube.puzzle_kind=='skewb_ultimate':
        # The oriented four-colour centres make the exact core search time out
        # on almost every scramble. The constructive core is fast and leaves
        # the saved seconds to the improvement search, which shortens the word.
        solution=list(solve_core(work,cancel,progress,exact=False))
    else:
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
    if cube.puzzle_kind == 'pyraminx' and cube.n == 5:
        # Fully restored orbits need no primitive discovery or transport BFS.
        targets = {i: orbit for i, orbit in targets.items()
                   if any(work.colors[s] != g.stickers[s].face
                          for piece in orbit for s in g.pieces[piece])}
    if targets:
        baseline=primitives(work,targets,cancel)
        macros=baseline
        order=list(targets)
        staged=None
        if cube.puzzle_kind=='fto':
            from solver.fto import prepared_stages
            plan=prepared_stages(work,targets)
            if plan is not None and _macro_cost(plan[0])<_macro_cost(baseline):
                staged,order=plan
                macros=staged
        # A hard orbit (long isolating commutator) can be built from far fewer
        # fixed stickers once the solved core is protected and the still
        # unsolved orbits may be disturbed. Solve hardest first so each such
        # orbit is guarded by the fewest solved stickers, and adopt the staged
        # plan only when it lowers the total macro cost.
        if staged is None and any(len(baseline[i][0])>_SHORT_PRIMITIVE for i in baseline):
            deep_order=sorted(targets,key=lambda i:-len(baseline[i][0]))
            guarded={s for i,orbit in enumerate(orbits) if i not in targets
                     for p in orbit for s in g.pieces[p]}
            protected={}
            for index in deep_order:
                protected[index]=set(guarded)
                guarded.update(s for p in targets[index] for s in g.pieces[p])
            try:
                candidate=primitives(work,targets,cancel,protected=protected)
            except ValueError:
                candidate=None
            if candidate is not None and _macro_cost(candidate)<_macro_cost(baseline):
                staged=candidate
                macros=candidate
                order=deep_order
        search_budget=(0.45 if cube.puzzle_kind=='skewb' and cube.n in (5,7) else 0.08)

        def alternatives_for(orbit):
            return len(g.pieces[orbit[0]])==1 or cube.puzzle_kind=='dino'

        if staged is None:
            # Isolated macros never disturb another orbit, so each orbit's
            # target permutation is fixed. Plan every orbit independently, then
            # order the plans to cancel turns where the orbits join.
            state=identify(work)
            plans=[]
            for index in order:
                if progress:
                    progress(len(plans),len(order))
                orbit=targets[index]
                indexes={p:i for i,p in enumerate(orbit)}
                destination=[None]*len(orbit)
                for home in orbit:
                    pos=g.stickers[state[g.pieces[home][0]]].piece
                    destination[indexes[pos]]=indexes[home]
                if not three_cycles(destination):
                    continue
                primitive,base=macros[index]
                transports=Transports(work,orbit,base,cancel,both_directions=True)
                word=orbit_word(transports,orbit,destination,primitive,solution,
                                alternatives=alternatives_for(orbit),
                                search_budget=search_budget)
                plans.append((index,word))
            pending=list(plans)
            prefix=simplify(solution,g.spec.turn_order)
            if len(plans) <= 4:
                from itertools import permutations
                best=None
                best_order=None
                for candidate in permutations(plans):
                    text=prefix
                    for _,word in candidate:
                        text=simplify(text+word,g.spec.turn_order)
                    if best is None or len(text)<len(best):
                        best=text
                        best_order=candidate
                ordered=[word for _,word in best_order]
            else:
                ordered=[]
                while pending:
                    if cancel and cancel():
                        raise InterruptedError()
                    choice=min(range(len(pending)),
                               key=lambda i:joined_length(prefix,pending[i][1],
                                                         g.spec.turn_order))
                    _,word=pending.pop(choice)
                    ordered.append(word)
                    prefix=simplify(prefix+word,g.spec.turn_order)
            for word in ordered:
                for move in word:
                    work.apply_move(move)
                solution.extend(word)
        else:
            for stage,index in enumerate(order):
                if cancel and cancel():
                    raise InterruptedError()
                if progress:
                    progress(stage,len(order))
                orbit=targets[index]
                state=identify(work)
                indexes={p:i for i,p in enumerate(orbit)}
                destination=[None]*len(orbit)
                for home in orbit:
                    pos=g.stickers[state[g.pieces[home][0]]].piece
                    destination[indexes[pos]]=indexes[home]
                primitive,base=macros[index]
                transports=Transports(work,orbit,base,cancel,both_directions=True)
                word=orbit_word(transports,orbit,destination,primitive,solution,
                                alternatives=alternatives_for(orbit),
                                search_budget=search_budget)
                for move in word:
                    work.apply_move(move)
                solution.extend(word)
    if not work.is_solved():
        raise ValueError('Polyhedral reduction replay failed')
    return simplify(solution,g.spec.turn_order)
