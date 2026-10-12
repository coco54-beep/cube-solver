"""Erase repeated complete visible states; accept only a solved full replay."""
from solver.polyhedral import inverse,simplify
from collections import OrderedDict

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


def shorten_polyhedral_word(cube,word,cancel=None):
    original=tuple(word)
    candidate=original
    if cube.puzzle_kind in _REWRITE_KINDS and len(cube.colors)<=256 and len(original)>32:
        from solver.pentahedron_high import _rewrite
        candidate=_rewrite(cube,original,_short_actions(cube,cancel),cancel)
    candidate=shorten_visible_loops(cube,candidate,cancel)
    if len(candidate)>=len(original):return original
    replay=cube.entered()
    for i,move in enumerate(candidate):
        if i%64==0 and cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    return tuple(candidate) if replay.is_solved() else original


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
            actions[move]=np.asarray(action,dtype=np.intp) if np is not None else action
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
    replay=cube.entered()
    for i,move in enumerate(candidate):
        if i%64==0:check()
        replay.apply_move(move)
    return tuple(candidate) if replay.is_solved() else original
