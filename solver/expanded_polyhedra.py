"""Colour-constrained finite-group solving for the new fixed-slot mechanisms.

The chain is built from actual layer actions, with no scramble witness. This
is a general correctness path; large groups may take substantial time. It is
cancellable during construction, colour matching and word expansion.
"""
from collections import Counter, OrderedDict
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
import json
import zlib
from cube.polyhedral import solved_colors

_CHAINS=OrderedDict()


@lru_cache(maxsize=6)
def _visible_piece_placements(kind,n):
    """Local colour orientations reached by real turns, including origins.

    Parallel cap axes do not generate all body orientations, and Siamese
    axes have different origins. Use actual panel actions to check input.
    """
    from collections import deque
    from cube.polyhedral import PolyhedralPuzzle
    cube=PolyhedralPuzzle(kind,n);g=cube.geometry;goal=solved_colors(cube)
    actions=tuple(g.permutation(m) for m in cube.moves())
    allowed={tuple((i,goal[i]) for i in sorted(piece)) for piece in g.pieces}
    queue=deque(allowed)
    while queue:
        state=queue.popleft()
        for action in actions:
            nxt=tuple(sorted((action[i],color) for i,color in state))
            if nxt not in allowed:allowed.add(nxt);queue.append(nxt)
    return frozenset(allowed)


def validate_expanded(cube):
    """Check visible pieces; the solver checks complete reachability."""
    from solver.polyhedral import piece_orbits
    goal=tuple(solved_colors(cube));start=tuple(cube.colors);g=cube.geometry
    if any(type(c) is not int or not 0<=c<cube.color_count for c in start):
        raise ValueError('Please enter every sticker')
    if Counter(start)!=Counter(goal):raise ValueError('The color counts do not match this puzzle')
    for orbit in piece_orbits(cube.puzzle_kind,cube.n):
        expected=Counter(tuple(sorted(goal[i] for i in g.pieces[p])) for p in orbit)
        entered=Counter(tuple(sorted(start[i] for i in g.pieces[p])) for p in orbit)
        if expected!=entered:raise ValueError('A piece has an impossible color combination or position')
    allowed=_visible_piece_placements(cube.puzzle_kind,cube.n)
    if any(tuple((i,start[i]) for i in sorted(piece)) not in allowed for piece in g.pieces):
        raise ValueError('A piece has a mirrored or impossible orientation')


def prepared_chain(cube):
    from solver.polyhedral import Word
    from solver.lattice_data import geometry_key
    data_kind=cube.puzzle_kind
    path=Path(__file__).parent/'data'/(data_kind+'_expanded_group.bin')
    if not path.exists():return None
    data=json.loads(zlib.decompress(path.read_bytes()))
    base=data.get('base',())
    if (data.get('version')!=1 or data.get('kind')!=data_kind or data.get('n')!=cube.n
            or data.get('geometry')!=geometry_key(cube.geometry) or sorted(base)!=list(range(len(cube.colors)))):
        raise ValueError('Expanded solver data does not match this mechanism')
    from cube.polyhedral import Move
    trans=[None]*len(base)
    for k,records in zip(base,data['transversals']):
        row={}
        for beta,record in records.items():
            word=Word()
            for atom in record['word']:word=word.then(Word(move=Move(*atom)))
            row[int(beta)]=(tuple(record['permutation']),word)
        trans[k]=row
    if any(row is None for row in trans):raise ValueError('Incomplete expanded solver data')
    return SimpleNamespace(trans=trans,base=tuple(base))


def solve_expanded(cube,cancel=None,progress=None):
    from solver.polyhedral import StabilizerChain, simplify
    if cancel and cancel():raise InterruptedError()
    validate_expanded(cube)
    goal=tuple(solved_colors(cube));start=tuple(cube.colors)
    if start==goal:return ()
    cache_key=(cube.puzzle_kind,cube.n)
    chain=_CHAINS.get(cache_key)
    if chain is None:
        if progress:progress(-1,0)
        chain=prepared_chain(cube)
        if chain is None:
            chain=StabilizerChain(cube,cancel,lambda *_:progress(-1,0) if progress else None)
        _CHAINS[cache_key]=chain
        while len(_CHAINS)>2:_CHAINS.popitem(last=False)
    else:_CHAINS.move_to_end(cache_key)
    # A transversal at k fixes all points above k. Solving those points in
    # descending order is an exhaustive coset search even for repeated colours.
    base=getattr(chain,'base',tuple(reversed(range(len(start)))))
    seen=set();factors=[]
    def choices(level,current):
        if current==goal:return iter((None,))
        if level>=len(base) or (level,current) in seen:return iter(())
        if len(seen)<12000:seen.add((level,current))
        k=base[level]
        items=[]
        for beta,(perm,word) in chain.trans[k].items():
            if current[beta]!=goal[k]:continue
            child=tuple(current[i] for i in perm)
            items.append((sum(a!=b for a,b in zip(child,goal)),word.length,beta,child,word))
        items.sort(key=lambda x:x[:3])
        return iter(items)
    stack=[(0,start,choices(0,start))]
    found=None;nodes=0
    while stack:
        if cancel and cancel():raise InterruptedError()
        level,current,items=stack[-1]
        item=next(items,False)
        if item is None:
            found=tuple(factors);break
        if item is False:
            stack.pop()
            if factors:factors.pop()
            continue
        _,_,_,child,word=item
        nodes+=1
        if progress and nodes%256==0:progress(-1,0)
        factors.append(word)
        stack.append((level+1,child,choices(level+1,child)))
    if found is None:raise ValueError('The entered puzzle is not a legal state')
    order=cube.geometry.spec.turn_order
    result=simplify(tuple(move for word in found for move in word.inverse().flatten(order,cancel)),order)
    replay=cube.entered()
    for move in result:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('Expanded puzzle solution replay failed')
    if progress:progress(1,1)
    return result
