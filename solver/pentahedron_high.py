"""Verified short-action rewriting for order-four and order-five prisms.

Rules preserve the entire sticker permutation. State-loop removal may also
remove excursions that only exchange indistinguishable pieces, and is checked
against the entered state before returning a result.
"""
from functools import lru_cache

from cube.polyhedral import Move,PolyhedralPuzzle
from solver.polyhedral import inverse,simplify


def _check(cancel):
    if cancel and cancel():
        raise InterruptedError()


@lru_cache(maxsize=2)
def _rules(n):
    cube=PolyhedralPuzzle('pentahedron',n)
    g=cube.geometry
    identity=bytes(range(len(g.stickers)))
    atoms={}
    for move in cube.moves():
        for power in range(1,g.spec.order(move.axis)):
            atom=Move(move.axis,move.layer,(g.spec.step(move.axis)*power)%g.spec.turn_order)
            permutation=bytes(g.permutation(atom))
            if permutation!=identity:
                atoms.setdefault(permutation,atom)
    rules={identity:()}
    frontier=[identity]
    for _ in range(3):
        following=[]
        for state in frontier:
            word=rules[state]
            for permutation,move in atoms.items():
                nxt=bytes(map(permutation.__getitem__,state))
                if nxt not in rules:
                    rules[nxt]=word+(move,)
                    following.append(nxt)
        frontier=following
    return rules,atoms


def _rewrite(cube,word,rules,cancel):
    g=cube.geometry
    identity=bytes(range(len(g.stickers)))
    result=list(word)
    index=0
    while index<len(result):
        if index%32==0:
            _check(cancel)
        permutation=identity
        best=None
        for stop in range(index,min(len(result),index+14)):
            action=g.permutation(result[stop])
            permutation=bytes(map(action.__getitem__,permutation))
            replacement=rules.get(permutation)
            if replacement is not None and len(replacement)<stop-index+1:
                gain=stop-index+1-len(replacement)
                if best is None or gain>best[0]:
                    best=(gain,stop+1,replacement)
        if best is None:
            index+=1
        else:
            _,stop,replacement=best
            result[index:stop]=replacement
            index=max(0,index-13)
    return simplify(result,g.spec.turn_order)


def _erase_state_loops(cube,word,cancel):
    g=cube.geometry
    state=bytes(cube.colors)
    signatures=[state]
    seen={state:0}
    result=[]
    actions={}
    for index,move in enumerate(word):
        if index%64==0:
            _check(cancel)
        action=actions.get(move)
        if action is None:
            action=inverse(g.permutation(move))
            actions[move]=action
        state=bytes(map(state.__getitem__,action))
        if state in seen:
            end=seen[state]
            for signature in signatures[end+1:]:
                del seen[signature]
            del signatures[end+1:]
            del result[end:]
        else:
            result.append(move)
            signatures.append(state)
            seen[state]=len(result)
    return simplify(result,g.spec.turn_order)


def shorten_pentahedron(cube,word,cancel=None):
    """Keep a replay-verified solution no longer than the original word."""
    if cube.puzzle_kind!='pentahedron' or cube.n not in (4,5):
        return tuple(word)
    _check(cancel)
    rules,_=_rules(cube.n)
    _check(cancel)
    original=tuple(word)
    best=simplify(original,cube.geometry.spec.turn_order)
    for _ in range(4):
        candidate=_erase_state_loops(cube,_rewrite(cube,best,rules,cancel),cancel)
        if len(candidate)>=len(best):
            break
        best=candidate
    if len(best)>=len(original):
        return original
    work=cube.entered()
    for index,move in enumerate(best):
        if index%64==0:
            _check(cancel)
        work.apply_move(move)
    return tuple(best) if work.is_solved() else original
