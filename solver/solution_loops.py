"""Erase repeated complete visible states; accept only a solved full replay."""
from solver.polyhedral import inverse,simplify
from collections import OrderedDict
from time import monotonic

_RULES=OrderedDict()
_REWRITE_KINDS={'fto','skewb','pyraminx','moyu','dino','war_drum','blossom','clover','eight_petals'}


def _short_actions(cube,cancel):
    key=(cube.puzzle_kind,cube.n)
    if key in _RULES:
        _RULES.move_to_end(key);return _RULES[key]
    from solver.polyhedral_optimize import _atoms
    g=cube.geometry;identity=bytes(range(len(g.stickers)))
    atoms={bytes(g.permutation(m)):m for m in _atoms(cube)}
    atoms.pop(identity,None)
    rules={identity:()};frontier=[identity]
    for _ in range(3):
        following=[]
        for i,state in enumerate(frontier):
            if i%64==0 and cancel and cancel():raise InterruptedError()
            for action,move in atoms.items():
                nxt=bytes(map(action.__getitem__,state))
                if nxt not in rules:
                    rules[nxt]=rules[state]+(move,);following.append(nxt)
                    if len(rules)>=60000:break
            if len(rules)>=60000:break
        frontier=following
        if len(rules)>=60000:break
    _RULES[key]=rules
    if len(_RULES)>2:_RULES.popitem(last=False)
    return rules


def _commute_reduce(cube,word,cancel=None,budget=1.0):
    """Bubble commuting turns together so adjacent turns can cancel.

    Turns with disjoint moving sets commute. Transport macros interleave setup
    moves from different axes, so a pure adjacent-block simplifier leaves
    many cancellations on the table. Reordering is only ever a swap of two
    commuting permutations, so the word stays equivalent.
    """
    if len(word)<8:
        return tuple(word)
    order=cube.geometry.spec.turn_order
    cache={}

    def support(move):
        key=(move.axis,move.layer,move.amount)
        value=cache.get(key)
        if value is None:
            perm=cube.geometry.permutation(move)
            value=frozenset(i for i,p in enumerate(perm) if p!=i)
            cache[key]=value
        return value

    deadline=monotonic()+max(0.0,budget)
    out=[]
    for index,move in enumerate(word):
        if index%64==0 and cancel and cancel():
            raise InterruptedError()
        if monotonic()>deadline:
            out.extend(word[index:])
            break
        moving=support(move)
        position=len(out)
        while position>0:
            previous=out[position-1]
            if ((previous.axis==move.axis and previous.layer==move.layer)
                    or support(previous).isdisjoint(moving)):
                position-=1
            else:
                break
        out.insert(position,move)
    return simplify(out,order)


def _replay_solved(cube,word,cancel=None):
    """Check a candidate word with a vectorised replay when numpy is present."""
    try:
        import numpy as np
    except ImportError:
        np=None
    if np is None:
        replay=cube.entered()
        for i,move in enumerate(word):
            if i%64==0 and cancel and cancel():raise InterruptedError()
            replay.apply_move(move)
        return replay.is_solved()
    from cube.polyhedral import solved_colors
    faces=np.fromiter(solved_colors(cube),dtype=np.int16,count=len(cube.colors))
    colors=np.asarray(cube.colors,dtype=np.int16)
    actions={}
    for i,move in enumerate(word):
        if i%256==0 and cancel and cancel():raise InterruptedError()
        action=actions.get(move)
        if action is None:
            action=np.asarray(cube.geometry.inverse_permutation(move),dtype=np.intp)
            actions[move]=action
        colors=colors[action]
    return bool(np.array_equal(colors,faces))


def shorten_polyhedral_word(cube,word,cancel=None):
    original=tuple(word)
    candidate=original
    if cube.puzzle_kind in _REWRITE_KINDS and len(cube.colors)<=256 and len(original)>32:
        from solver.pentahedron_high import _rewrite
        candidate=_rewrite(cube,original,_short_actions(cube,cancel),cancel)
    if len(candidate)>32:
        candidate=_commute_reduce(cube,candidate,cancel,
                                  budget=min(1.5,0.15+len(candidate)/6000.0))
    candidate=shorten_visible_loops(cube,candidate,cancel)
    if len(candidate)>=len(original):return original
    return tuple(candidate) if _replay_solved(cube,candidate,cancel) else original


def shorten_visible_loops(cube,word,cancel=None):
    original=tuple(word)
    if len(original)<32 or cube.puzzle_kind=='mirror_tower':
        return original
    def check():
        if cancel and cancel():raise InterruptedError()
    check()
    try:
        import numpy as np
    except ImportError:
        np=None
    state=bytes(cube.colors)
    signatures=[state];seen={state:0};result=[];actions={}
    # Retain at most 16 MiB of sticker states, including high-order minxes.
    limit=max(64,16*1024*1024//max(1,len(state)))
    offset=0
    for i,move in enumerate(original):
        if i%64==0:check()
        if move not in actions:
            action=inverse(cube.geometry.permutation(move))
            actions[move]=(np.asarray(action,dtype=np.uint16 if len(state)<=65536 else np.uint32)
                           if np is not None else action)
        action=actions[move]
        state=(np.frombuffer(state,dtype=np.uint8)[action].tobytes() if np is not None
               else bytes(map(state.__getitem__,action)))
        end=seen.get(state)
        if end is not None:
            for signature in signatures[end-offset+1:]:del seen[signature]
            del signatures[end-offset+1:]
            del result[end:]
        else:
            result.append(move);signatures.append(state);seen[state]=len(result)
        if len(signatures)>limit:
            offset=len(result);signatures=[state];seen={state:offset}
    candidate=simplify(result,cube.geometry.spec.turn_order)
    if len(candidate)>=len(original):return original
    return tuple(candidate) if _replay_solved(cube,candidate,cancel) else original
