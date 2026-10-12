"""Pair flipped Tuttminx core edges using verified short conjugate words."""
from functools import lru_cache
from heapq import heappop,heappush

from cube.polyhedral import Move
from solver.polyhedral import simplify

_CACHE={}


def _check(cancel):
    if cancel and cancel():
        raise InterruptedError()


def _mask(vector):
    return sum((int(value)&1)<<i for i,value in enumerate(vector))


def _generators(cube,record,cancel):
    from solver.football import EdgePositions,edge_units
    key=(cube.n,record['geometry'])
    # geometry keys are JSON strings in the bundled records.
    if key in _CACHE:
        return _CACHE[key]
    g=cube.geometry
    model=EdgePositions(cube)
    identity=tuple(range(len(model.originals)))
    atoms={}
    for move in cube.moves():
        _check(cancel)
        for power in range(1,g.spec.order(move.axis)):
            atom=Move(move.axis,move.layer,power*g.spec.step(move.axis))
            permutation=model.geometry.permutation(atom)
            if permutation!=identity:
                atoms.setdefault(permutation,atom)
    words={}
    distances={}
    heap=[]
    for relation in record['edge_flips']:
        mask=_mask(relation['vector'])
        if mask.bit_count()!=2:
            raise ValueError('Expected pair-flip Tuttminx relations')
        word=tuple(Move(*move) for move in relation['word'])
        if mask not in distances or len(word)<distances[mask]:
            words[mask]=word;distances[mask]=len(word)
            heappush(heap,(len(word),mask))
    visits=0
    while heap:
        cost,mask=heappop(heap)
        if distances[mask]!=cost:
            continue
        visits+=1
        if visits%32==0:
            _check(cancel)
        a=(mask&-mask).bit_length()-1
        other=mask^(1<<a)
        b=other.bit_length()-1
        for permutation,atom in atoms.items():
            nxt=(1<<permutation[a])|(1<<permutation[b])
            next_cost=cost+2
            if nxt not in distances or next_cost<distances[nxt]:
                distances[nxt]=next_cost
                words[nxt]=simplify((atom.inverse(g.spec.turn_order),)+words[mask]+(atom,),
                                   g.spec.turn_order)
                heappush(heap,(next_cost,nxt))
    # Certify every generated word on all sixty core stickers, including
    # positions. Other orbits are deliberately left for the remaining solve.
    points,units=edge_units(cube)
    index={s:i for i,s in enumerate(points)}
    permutations={}
    for mask,word in words.items():
        _check(cancel)
        action=tuple(range(len(points)))
        for move in word:
            permutation=permutations.get(move)
            if permutation is None:
                full=g.permutation(move)
                permutation=tuple(index[full[s]] for s in points)
                permutations[move]=permutation
            action=tuple(map(permutation.__getitem__,action))
        expected=list(range(len(points)))
        for i,pair in enumerate(units[2]):
            if mask&(1<<i):
                a,b=pair;expected[a],expected[b]=expected[b],expected[a]
        if action!=tuple(expected):
            raise ValueError('Football pair-flip word does not match its core action')
    _CACHE[key]=words
    return words


def paired_flip_word(cube,record,vector,cancel=None):
    """Find a short pair decomposition; None retains the existing basis solve.

    Small targets use exact minimum-cost matching over prepared pair words.
    Larger targets use greedy matching and improving four-endpoint swaps.
    Neither mode claims a globally optimal complete puzzle solution.
    """
    _check(cancel)
    mask=_mask(vector)
    if not mask:
        return ()
    if mask.bit_count()%2:
        return None
    words=_generators(cube,record,cancel)
    points=[i for i in range(len(vector)) if mask&(1<<i)]
    size=len(points)
    costs={}
    for a in range(size):
        for b in range(a+1,size):
            word=words.get((1<<points[a])|(1<<points[b]))
            if word is None:
                return None
            costs[a,b]=len(word)
    def cost(a,b):
        return costs[min(a,b),max(a,b)]
    if size<=16:
        calls=0
        @lru_cache(maxsize=None)
        def match(remaining):
            nonlocal calls
            calls+=1
            if calls%128==0:
                _check(cancel)
            if not remaining:
                return 0,()
            bit=remaining&-remaining
            a=bit.bit_length()-1
            tail=remaining^bit
            choices=tail
            best=None
            while choices:
                bit=choices&-choices;choices^=bit
                b=bit.bit_length()-1
                price,pairs=match(tail^bit)
                candidate=(price+cost(a,b),((a,b),)+pairs)
                if best is None or candidate[0]<best[0]:
                    best=candidate
            return best
        _,pairs=match((1<<size)-1)
    else:
        left=set(range(size));pairs=[]
        while left:
            a,b=min(((a,b) for a in sorted(left) for b in sorted(left) if a<b),
                    key=lambda pair:cost(*pair))
            pairs.append((a,b));left.remove(a);left.remove(b)
        for _ in range(size):
            _check(cancel)
            changed=False
            for i in range(len(pairs)):
                a,b=pairs[i]
                for j in range(i+1,len(pairs)):
                    c,d=pairs[j]
                    old=cost(a,b)+cost(c,d)
                    options=[((a,c),(b,d)),((a,d),(b,c))]
                    replacement=min(options,key=lambda p:sum(cost(*pair) for pair in p))
                    if sum(cost(*pair) for pair in replacement)<old:
                        pairs[i],pairs[j]=replacement
                        a,b=pairs[i];changed=True
            if not changed:
                break
    return simplify((move for a,b in pairs
                     for move in words[(1<<points[a])|(1<<points[b])]),
                    cube.geometry.spec.turn_order)
