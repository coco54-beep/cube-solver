"""Bounded rigid-state search; never return an unverified solution."""
from time import monotonic
from cube.polyhedral import Move


def solve_articulated(cube,cancel=None,progress=None):
    if cube.is_solved():return ()
    if getattr(cube,'puzzle_kind',None)=='pentacle':
        from solver.pentacle import solve_pentacle
        return solve_pentacle(cube,cancel,progress)
    if getattr(cube,'puzzle_kind',None) in ('tangram','tangram_extreme'):
        from solver.tangram import solve_tangram
        return solve_tangram(cube,cancel,progress)
    period=cube.geometry.spec.turn_order
    if cube.history and cube.frames==cube._history_snapshot:
        word=tuple(m.inverse(period) for m in reversed(cube.history))
        replay=cube.clone()
        for move in word:
            if cancel and cancel():raise InterruptedError()
            replay.apply_move(move)
        if replay.is_solved():
            shorter=_simplify_rigid(cube,word)
            if len(shorter)<len(word):
                check=cube.clone()
                try:
                    check.apply_moves(shorter)
                except ValueError:
                    check=None
                if check is not None and check.is_solved():
                    return shorter
            return word
    # Manual entries have no trusted scramble. A strict resource budget keeps
    # an unfamiliar/deep state from blocking the phone or exhausting memory.
    deadline=monotonic()+8.;nodes=0
    def guard():
        if cancel and cancel():raise InterruptedError()
        if nodes>10000 or monotonic()>deadline:raise ValueError('rigid.search_limit')
    def visit(state,depth,path,last,seen):
        nonlocal nodes
        nodes+=1
        if cancel and cancel():raise InterruptedError()
        if nodes>10000 or monotonic()>deadline:raise ValueError('rigid.search_limit')
        if state.is_solved():return tuple(path)
        if depth==0:return None
        if seen.get(state.frames,-1)>=depth:return None
        seen[state.frames]=depth
        for base in state.moves():
            if last==(base.axis,base.layer):continue
            for amount in range(base.amount,period,base.amount):
                move=Move(base.axis,base.layer,amount)
                child=state.clone()
                try:child.apply_move(move,guard=guard)
                except ValueError as exc:
                    if str(exc)=='rigid.search_limit':raise
                    continue
                answer=visit(child,depth-1,path+[move],(move.axis,move.layer),seen)
                if answer is not None:return answer
        return None
    for depth in range(1,7):
        if progress:progress(depth,6)
        answer=visit(cube.clone(),depth,[],None,{})
        if answer is not None:
            replay=cube.clone();replay.apply_moves(answer)
            if not replay.is_solved():raise ValueError('rigid.invalid')
            return answer
    raise ValueError('rigid.search_limit')

def _simplify_rigid(cube, word):
    """Cancel adjacent turns on the same rigid axis/layer."""
    order = cube.geometry.spec.turn_order
    result = []
    for move in word:
        if result and (move.axis, move.layer) == (result[-1].axis, result[-1].layer):
            amount = (result[-1].amount + move.amount) % order
            result.pop()
            if amount:
                result.append(type(move)(move.axis, move.layer, amount))
        else:
            result.append(move)
    return tuple(result)

