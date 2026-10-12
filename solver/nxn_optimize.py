"""Colour-aware centre planning for ordinary higher order cubes."""
from collections import OrderedDict
from heapq import heappop, heappush

from cube.coordinates import get_d_maxc, FACE_NORMALS, FACE_AXIS_SIGN
from solver import nxn_orbits as orbit


_ROUTES = OrderedDict()


def _cycle_key(triple):
    a, b, c = triple
    return min((a, b, c), (b, c, a), (c, a, b))


def _routes(n, positions, base, start, cancel):
    """Shortest setup by visible slice cost, using either cycle direction.

    Cyclic rotations of three markers describe the same operation. An inner
    slice expands to two player moves, whereas an outer face costs one.
    Cache completed tables only, and bound retained memory on large orders.
    """
    key = n, positions, tuple(base), start
    if key in _ROUTES:
        _ROUTES.move_to_end(key)
        return _ROUTES[key]
    gen = orbit.generators(n, positions)
    maps = orbit._conjug_maps(n, positions)
    _, m = get_d_maxc(n)
    weights = [1 if abs(coordinate) == m else 2 for _, coordinate, _ in gen]
    # Re-label a proven formula along all 24 cube orientations. This changes
    # the formula's axes directly and requires no physical cube rotations.
    indexes = {p: i for i, p in enumerate(positions)}
    faces = {normal: face for face, normal in FACE_NORMALS.items()}
    bases = []
    distances, parents, roots, queue = {}, {}, {}, []
    for rot in orbit.rotations():
        rotated = []
        for face, coordinate, count in base:
            axis = FACE_AXIS_SIGN[face][0]
            point = [0, 0, 0]
            point[axis] = coordinate
            new_face = faces[rot(FACE_NORMALS[face])]
            new_axis = FACE_AXIS_SIGN[new_face][0]
            rotated.append((new_face, rot(tuple(point))[new_axis], count))
        triple = tuple(indexes[rot(positions[i])] for i in start)
        for atoms, trip in ((rotated, triple),
                            (orbit.inverse(rotated), (triple[0], triple[2], triple[1]))):
            state = _cycle_key(trip)
            cost = len(orbit.expand(atoms, n))
            if cost < distances.get(state, float('inf')):
                roots[state] = len(bases)
                bases.append(atoms)
                distances[state] = cost
                parents[state] = None
                heappush(queue, (cost, state))
    visits = 0
    while queue:
        cost, state = heappop(queue)
        if cost != distances[state]:
            continue
        visits += 1
        if visits % 128 == 0:
            cancel()
        for i, mapping in enumerate(maps):
            nxt = _cycle_key(tuple(mapping[j] for j in state))
            new_cost = cost + 2*weights[i]
            if new_cost < distances.get(nxt, float('inf')):
                distances[nxt] = new_cost
                parents[nxt] = state, i
                roots[nxt] = roots[state]
                heappush(queue, (new_cost, nxt))
    table = gen, distances, parents, roots, bases
    _ROUTES[key] = table
    if len(_ROUTES) > 8:
        _ROUTES.popitem(last=False)
    return table


def _algorithm(table, target):
    gen, _, parents, roots, bases = table
    setup, cur = [], target
    while parents[cur] is not None:
        cur, i = parents[cur]
        setup.append(gen[i])
    setup.reverse()
    primitive = bases[roots[target]]
    return orbit.inverse(setup) + primitive + setup


def wing_atoms(n, positions, base, start, targets, cancel):
    """Shorten each wing cycle without changing its piece permutation."""
    table = _routes(n, positions, base, start, cancel)
    legacy = orbit.conjugates(n, positions, base, start, targets, cancel)
    from solver.solver_n import _compress
    for target, original in zip(targets, legacy):
        cancel()
        candidate = _algorithm(table, _cycle_key(target))
        def cost(atoms):
            return len(_compress(orbit.expand(atoms, n), n))
        yield candidate if cost(candidate) < cost(original) else original


def center_atoms(cube, positions, cancel, strategies=(0,1,2),return_options=False):
    """Prefer useful colour cycles to arbitrary labels of same-colour pieces.

    Every selected cycle strictly reduces incorrect colours. A same-colour
    spare centre can absorb the parity of a two-piece colour swap. Compare
    the complete emitted sequence against the original planner and retain
    the shorter one, including cancellations between adjacent cycles.
    """
    perm = orbit.center_permutation(cube, positions)
    targets = orbit.three_cycles(perm)
    if not targets:
        return ([],[]) if return_options else []
    base, start = orbit.primitive(cube.n, positions, False, cancel)
    legacy = [atom for seq in orbit.conjugates(cube.n, positions, base, start,
                                               targets, cancel) for atom in seq]
    table = _routes(cube.n, positions, base, start, cancel)
    solved = orbit._solved(cube.n)
    expected = [next(iter(solved.cubies[p].stickers.values())) for p in positions]
    actual = [next(iter(cube.cubies[p].stickers.values())) for p in positions]
    candidates = tuple(table[1].items())
    try:
        import numpy as np
    except ImportError:
        np=None
    if np is not None:
        triples=np.asarray([triple for triple,_ in candidates],dtype=np.intp)
        a,b,c=triples.T
        costs=np.asarray([cost for _,cost in candidates],dtype=float)
        colors={value:i for i,value in enumerate(dict.fromkeys(expected+actual))}
        goal=np.asarray([colors[value] for value in expected])
        proposals=[]
        for strategy in strategies:
            state=np.asarray([colors[value] for value in actual])
            word=[]
            while not np.array_equal(state,goal):
                cancel()
                correct=state==goal
                aa,bb,cc=state[c]==goal[a],state[a]==goal[b],state[b]==goal[c]
                gain=(aa.astype(int)+bb+cc-correct[a].astype(int)-correct[b]-correct[c])
                disturbed=((correct[a]&~aa).astype(int)+(correct[b]&~bb)+(correct[c]&~cc))
                valid=np.flatnonzero(gain>0)
                if not len(valid):
                    word=None;break
                if strategy==0:
                    ranking=np.lexsort((costs[valid],disturbed[valid],-gain[valid],
                                        -gain[valid]/costs[valid]))
                elif strategy==1:
                    ranking=np.lexsort((disturbed[valid],costs[valid],-gain[valid]))
                else:
                    ranking=np.lexsort((costs[valid],-gain[valid],disturbed[valid],
                                        -gain[valid]/(costs[valid]+1)))
                i=int(valid[ranking[0]])
                triple=tuple(int(x) for x in triples[i])
                word.extend(_algorithm(table,triple))
                x,y,z=triple
                state[x],state[y],state[z]=int(state[z]),int(state[x]),int(state[y])
            if word is not None:
                proposals.append((strategy,word))
        from solver.solver_n import _compress
        def cost(word):return len(_compress(orbit.expand(word,cube.n),cube.n))
        baseline=min([legacy]+[word for strategy,word in proposals if strategy==0],key=cost)
        best=min([legacy]+[word for _,word in proposals],key=cost)
        return (baseline,best) if return_options else best
    planned = []
    while actual != expected:
        cancel()
        best = None
        best_rank = None
        correct = [a == b for a, b in zip(actual, expected)]
        for (a, b, c), cost in candidates:
            after = (actual[c] == expected[a], actual[a] == expected[b],
                     actual[b] == expected[c])
            gain = sum(after) - (correct[a] + correct[b] + correct[c])
            if gain <= 0:
                continue
            disturbed = sum(was and not now for was, now in
                            zip((correct[a], correct[b], correct[c]), after))
            rank = (gain / cost, gain, -disturbed, -cost)
            if best_rank is None or rank > best_rank:
                best, best_rank = (a, b, c), rank
        if best is None:
            return (legacy,legacy) if return_options else legacy
        planned.extend(_algorithm(table, best))
        a, b, c = best
        actual[a], actual[b], actual[c] = actual[c], actual[a], actual[b]
    from solver.solver_n import _compress
    def player_cost(atoms):
        return len(_compress(orbit.expand(atoms, cube.n), cube.n))
    best=planned if player_cost(planned) < player_cost(legacy) else legacy
    return (best,best) if return_options else best


def identity_center_atoms(cube,positions,cancel):
    """Compare weighted setups while keeping the exact centre-piece cycle."""
    targets=orbit.three_cycles(orbit.center_permutation(cube,positions))
    if not targets:
        return []
    base,start=orbit.primitive(cube.n,positions,False,cancel)
    return [atom for word in wing_atoms(cube.n,positions,base,start,targets,cancel)
            for atom in word]
