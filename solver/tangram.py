"""Bounded macro search for the two Tangram mechanisms."""
from time import monotonic
from solver.articulated import _simplify_rigid


def _score(cube):
    # Number of solids away from their home pose; lower is better.
    return sum(1 for pose in cube.frames if pose != 0)


def _verify(cube, word, cancel):
    work = cube.clone()
    for move in word:
        if cancel and cancel(): raise InterruptedError()
        try: work.apply_move(move)
        except ValueError: return False
    return work.is_solved()


def solve_tangram(cube, cancel=None, progress=None):
    if cube.is_solved(): return ()
    period = cube.geometry.spec.turn_order
    if cube.history and cube.frames == cube._history_snapshot:
        word = tuple(m.inverse(period) for m in reversed(cube.history))
        if _verify(cube, word, cancel):
            short = _simplify_rigid(cube, word)
            if len(short) < len(word) and _verify(cube, short, cancel): return short
            return word
    deadline = monotonic() + 10.
    start = cube.clone(); beam = [(_score(start), start, ())]; seen = {start.frames}
    width = 120
    for depth in range(1, 25):
        if cancel and cancel(): raise InterruptedError()
        if progress: progress(depth, 24)
        following = []
        for _, state, path in beam:
            if monotonic() > deadline: break
            previous = (path[-1].axis, path[-1].layer) if path else None
            for base in state.moves():
                if previous == (base.axis, base.layer): continue
                for amount in range(base.amount, period, base.amount):
                    from cube.polyhedral import Move
                    move = Move(base.axis, base.layer, amount)
                    child = state.clone()
                    try: child.apply_move(move)
                    except ValueError: continue
                    if child.frames in seen: continue
                    seen.add(child.frames); word = path + (move,)
                    if child.is_solved():
                        if _verify(cube, word, cancel): return word
                    following.append((_score(child), child, word))
        if not following: break
        following.sort(key=lambda item: item[0]); beam = following[:width]
        if monotonic() > deadline: break
    raise ValueError('rigid.search_limit')
