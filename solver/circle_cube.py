"""Replay-verified Circle solutions from a history or an entered colour state."""
from collections import Counter
from functools import lru_cache
from cube.polyhedral import Move
from solver.polyhedral import inverse_word,simplify


def validate_circle(cube):
    from solver.messages import tr
    goal=tuple(s.face for s in cube.geometry.stickers)
    if any(type(c) is not int or not 0<=c<6 for c in cube.colors) or Counter(cube.colors)!=Counter(goal):
        raise ValueError(tr('circle.count_error'))
    # This checks necessary colour counts, not full reachability.
    return goal


def _atoms(cube):
    return tuple(Move(a,0,k) for a in range(len(cube.geometry.spec.axes)) for k in (1,2,3))


def solve_circle(cube,cancel=None,progress=None):
    if cube.puzzle_kind=='circle_2':cube=cube.entered()
    validate_circle(cube)
    if cancel and cancel():raise InterruptedError()
    if cube.is_solved():return ()
    def verified(word):
        replay=cube.entered()
        for move in word:
            if cancel and cancel():raise InterruptedError()
            replay.apply_move(move)
        return replay.is_solved()
    # Keep the witness only after matching all entered colours. Painting
    # or restoring unrelated state can never yield a false successful answer.
    history=getattr(cube,'circle_history',None)
    if history is not None:
        result=simplify(inverse_word(history,4),4)
        if verified(result):
            if progress:progress(1,1)
            return result
    from solver.circle2_group import solve_circle_group
    try:return solve_circle_group(cube,cancel,progress)
    except ValueError as error:
        from solver.messages import tr
        key=str(error)
        if key.startswith(('circle.','circle2.')):raise ValueError(tr(key)) from None
        raise


@lru_cache(maxsize=8)
def _circle2_maps(anchor):
    import math
    from cube.circle_cube import Circle2Cube
    from cube.polyhedral import rotate
    cube=Circle2Cube(anchor=anchor);result=[]
    for move in _atoms(cube):
        normal=cube.geometry.spec.axes[move.axis]
        a,sign=next((a,v) for a,v in enumerate(normal) if v)
        target=(tuple(round(v) for v in rotate(anchor,normal,move.amount*math.pi/2))
                if anchor[a]==sign else anchor)
        result.append((move,cube.geometry.inverse_permutation(move),target))
    return tuple(result)


