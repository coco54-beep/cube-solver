"""Replay-verified Circle solutions, with a bounded search for short input states.

This deliberately does not pretend an ordinary 3x3 solution restores the disc.
A general state-based planet reduction remains a separate solver project.
"""
from collections import Counter,deque
from functools import lru_cache
from time import monotonic
from cube.polyhedral import Move,PolyhedralPuzzle
from solver.polyhedral import inverse_word,simplify


def validate_circle(cube):
    from solver.messages import tr
    goal=tuple(s.face for s in cube.geometry.stickers)
    if any(type(c) is not int or not 0<=c<6 for c in cube.colors) or Counter(cube.colors)!=Counter(goal):
        raise ValueError(tr('circle.count_error'))
    # This checks necessary colour counts, not full reachability.
    return goal


def _atoms(cube):
    return tuple(Move(a,0,k) for a in range(6) for k in (1,2,3))


@lru_cache(maxsize=1)
def _goal_ball(kind):
    cube=PolyhedralPuzzle(kind,3);atoms=_atoms(cube)
    maps=tuple(cube.geometry.inverse_permutation(m) for m in atoms)
    goal=bytes(cube.colors);records={goal:()};front=[goal]
    for depth in range(3):
        nxt=[]
        for state in front:
            word=records[state]
            for move,mapping in zip(atoms,maps):
                if word and word[-1].axis==move.axis:continue
                target=bytes(map(state.__getitem__,mapping))
                if target not in records:
                    records[target]=word+(move,);nxt.append(target)
        front=nxt
    return records


def solve_circle(cube,cancel=None,progress=None):
    goal=validate_circle(cube)
    if cancel and cancel():raise InterruptedError()
    if cube.is_solved():return ()
    g=cube.geometry
    def verified(word):
        replay=PolyhedralPuzzle(cube.puzzle_kind,3,cube.colors)
        for move in word:
            if cancel and cancel():raise InterruptedError()
            replay.apply_move(move)
        return replay.is_solved()
    # Keep the witness only after matching all 102 entered colours. Painting
    # or restoring unrelated state can never yield a false successful answer.
    history=getattr(cube,'circle_history',None)
    if history is not None:
        result=simplify(inverse_word(history,4),4)
        if verified(result):
            if progress:progress(1,1)
            return result
    start=monotonic();atoms=_atoms(cube)
    maps=tuple(g.inverse_permutation(m) for m in atoms)
    solved=_goal_ball(cube.puzzle_kind)
    state=bytes(cube.colors);pending=deque([(state,())]);seen={state}
    while pending:
        if cancel and cancel():raise InterruptedError()
        if monotonic()-start>4:break
        state,word=pending.popleft()
        tail=solved.get(state)
        if tail is not None:
            result=simplify(word+inverse_word(tail,4),4)
            if not verified(result):raise ValueError('Circle solution replay failed')
            if progress:progress(1,1)
            return result
        if len(word)>=3:continue
        for move,mapping in zip(atoms,maps):
            if word and move.axis==word[-1].axis:continue
            nxt=bytes(map(state.__getitem__,mapping))
            if nxt not in seen:
                seen.add(nxt);pending.append((nxt,word+(move,)))
    from solver.messages import tr
    raise ValueError(tr('circle.search_limit'))
