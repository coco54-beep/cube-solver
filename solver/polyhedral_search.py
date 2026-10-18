"""Pattern databases and bounded-depth search for small polyhedral cores."""
from collections import deque
from functools import lru_cache
import time

from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import piece_orbits, inverse, simplify


_DATABASES={}


def core_database(kind,n,cancel=None):
    cached=_DATABASES.get((kind,n))
    if cached is not None:
        return cached
    if cancel and cancel():
        raise InterruptedError()
    cube=PolyhedralPuzzle(kind,n)
    g=cube.geometry
    orbits=piece_orbits(kind,n)
    tips={layers[0][0] for layers in g.layers if len(layers[0])==1}
    if kind!='pyraminx' or n<3:
        tips=set()
    # Pyraminx tips can be set independently after the interacting core.
    # Including them in IDA multiplies equivalent branches needlessly.
    selected=[o for o in orbits if (kind=='clover' or 1<len(o)<=6 or len(g.pieces[o[0]])==3)
              and o[0] not in tips]
    points=tuple(s for orbit in selected for piece in orbit for s in g.pieces[piece])
    index={s:i for i,s in enumerate(points)}
    goal=bytes(g.stickers[s].face for s in points)
    moves=[]
    maps=[]
    seen=set()
    for move in cube.moves():
        for atom in (move,move.inverse(g.spec.turn_order)):
            full=g.permutation(atom)
            perm=tuple(index[full[s]] for s in points)
            if perm==tuple(range(len(points))) or perm in seen:
                continue
            seen.add(perm)
            moves.append(atom)
            maps.append(inverse(perm))
    patterns=[]
    for orbit in selected:
        ids=tuple(index[s] for piece in orbit for s in g.pieces[piece])
        pattern_index={s:i for i,s in enumerate(ids)}
        perms=[tuple(pattern_index[perm[s]] for s in ids) for perm in maps]
        start=bytes(goal[s] for s in ids)
        distances={start:0}
        queue=deque([start])
        expanded=0
        while queue:
            expanded+=1
            if expanded%256==0 and cancel and cancel():
                raise InterruptedError()
            state=queue.popleft()
            depth=distances[state]+1
            for perm in perms:
                nxt=bytes(map(state.__getitem__, perm))
                if nxt not in distances:
                    distances[nxt]=depth
                    queue.append(nxt)
            if len(distances)>100_000:
                raise ValueError('This core orbit is too large for the pattern database')
        patterns.append((ids,distances))
    parent=list(range(len(patterns)))
    def find(i):
        while parent[i]!=i:
            i=parent[i]
        return i
    touched=[]
    for perm in maps:
        active=[j for j,(ids,_) in enumerate(patterns) if any(perm[i]!=i for i in ids)]
        touched.append(set(active))
        for i in active[1:]:
            parent[find(i)]=find(active[0])
    components={}
    for i in range(len(patterns)):
        components.setdefault(find(i),[]).append(i)
    groups=tuple((tuple(indices),max(len(set(indices)&active) for active in touched))
                 for indices in components.values())
    result=points,goal,tuple(moves),tuple(maps),tuple(patterns),groups
    if len(_DATABASES)>=3:
        _DATABASES.pop(next(iter(_DATABASES)))
    _DATABASES[(kind,n)]=result
    return result


def _search_core(cube,cancel=None,progress=None,max_seconds=2):
    points,goal,moves,maps,patterns,groups=core_database(cube.puzzle_kind,cube.n,cancel)
    state=bytes(cube.colors[i] for i in points)
    if state==goal:
        return ()
    start=time.monotonic()
    count=0
    hcache={}

    def heuristic(state):
        h=hcache.get(state)
        if h is not None:
            return h
        values=[]
        append=values.append
        for ids,distances in patterns:
            pattern=bytes(map(state.__getitem__, ids))
            if pattern not in distances:
                raise ValueError('The entered core has an impossible orientation')
            append(distances[pattern])
        total=0
        for ids,affected in groups:
            group_max=0
            group_sum=0
            for i in ids:
                value=values[i]
                group_sum+=value
                if value>group_max:
                    group_max=value
            mean=(group_sum+affected-1)//affected
            total+=group_max if group_max>mean else mean
        if cube.puzzle_kind != 'skewb_ultimate' or len(hcache) < 20000:
            hcache[state]=total
        return total

    path=[]
    # Ultimate's four-colour centres expose orientation, unlike plain Skewb.
    # Different move orders often revisit exactly the same oriented state.
    # Cache failed subtrees per IDA bound, retaining at most ~20k entries.
    failed = {} if cube.puzzle_kind == 'skewb_ultimate' else None
    def search(state,remaining,last):
        nonlocal count
        count+=1
        if count%2048==0:
            if cancel and cancel():
                raise InterruptedError()
            if time.monotonic()-start>max_seconds:
                raise TimeoutError('Use the constructive core solver')
        h=heuristic(state)
        if h>remaining:
            return False
        if state==goal:
            return True
        if not remaining:
            return False
        marker = (state, last)
        if failed is not None and failed.get(marker, -1) >= remaining:
            return False
        for i,(move,perm) in enumerate(zip(moves,maps)):
            if last is not None and (move.axis,move.layer)==last:
                # Two inverse generators can require a double turn on minx;
                # tetrahedral cores have turn order three, so this is safe.
                continue
            path.append(move)
            if search(bytes(map(state.__getitem__, perm)),remaining-1,(move.axis,move.layer)):
                return True
            path.pop()
        if failed is not None and len(failed) < 20000:
            failed[marker] = remaining
        return False

    for depth in range(heuristic(state),23):
        if failed is not None:
            failed.clear()
        if progress:
            progress(depth,22)
        if search(state,depth,None):
            return simplify(path,cube.geometry.spec.turn_order)
    raise ValueError('Core search did not find a legal solution')


_CORE_CHAINS={}


def solve_core(cube,cancel=None,progress=None,max_seconds=2,exact=True):
    """Try a short solution, then use a constructive stabilizer solution.

    ``exact=False`` skips the bounded IDA search and goes straight to the
    constructive chain. The improvement search re-solves the puzzle many times
    and the IDA attempt is far too slow to repeat on each call.
    """
    if exact:
        try:
            return _search_core(cube,cancel,progress,max_seconds)
        except (TimeoutError, ValueError):
            pass
    if cube.puzzle_kind=='fto':
        # Safety net: the compact PDB may not cover every state.
        from solver.fto import solve_prepared_core
        prepared=solve_prepared_core(cube,cancel,progress)
        if prepared is not None:
            return prepared
    from solver.polyhedral import StabilizerChain,identify
    if cube.puzzle_kind == 'fto':
        from solver.fto import core_points
        points=core_points(cube)
    else:
        points=core_database(cube.puzzle_kind,cube.n,cancel)[0]
    point_index={s:i for i,s in enumerate(points)}
    full=identify(cube)
    state=tuple(point_index[full[s]] for s in points)
    key=(cube.puzzle_kind,cube.n)
    chain=_CORE_CHAINS.get(key)
    if chain is None:
        chain=StabilizerChain(cube,cancel,progress,points)
        _CORE_CHAINS.clear()
        _CORE_CHAINS[key]=chain
    word=chain.solve(state)
    return simplify(word.flatten(cube.geometry.spec.turn_order,cancel),cube.geometry.spec.turn_order)
