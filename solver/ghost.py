"""Solve real Ghost layer offsets as well as the hidden cubie mechanism."""
from time import perf_counter

from solver.result import SolveResult, SolveStage


def _floppy(cube, cancelled):
    from cube.ghost_floppy import state_key, turn_state
    start, goal = state_key(cube), tuple(range(5)) + (0, 0)
    if start == goal:
        return []
    # Search compact states from both ends, preserving every corner's facing.
    parents = ({start: None}, {goal: None})
    fronts = ({start}, {goal})
    while fronts[0] and fronts[1]:
        if cancelled():
            raise InterruptedError()
        direction = 0 if len(fronts[0]) <= len(fronts[1]) else 1
        next_front = set()
        for state in fronts[direction]:
            if cancelled():
                raise InterruptedError()
            for side in range(5):
                target = turn_state(state, side)
                if target in parents[direction]:
                    continue
                parents[direction][target] = (state, side)
                if target in parents[1-direction]:
                    words = []
                    for parent in parents:
                        word, cursor = [], target
                        while parent[cursor] is not None:
                            cursor, move = parent[cursor]
                            word.append('@F:'+str(move+1))
                        words.append(word)
                    return list(reversed(words[0])) + words[1]
                next_front.add(target)
        fronts[direction] = next_front
    raise ValueError('ghost.invalid')


def solve_ghost(cube, cancel_event=None, progress_callback=None):
    from cube.conversion import cubies_to_facelets
    started = perf_counter()
    cancelled = lambda: cancel_event is not None and cancel_event.is_set()
    if cancelled():
        raise InterruptedError()
    if cube.is_solved():
        return SolveResult(True, [], '', 0, 0, [])
    if cube.n == 1:
        try:
            moves = _floppy(cube, cancelled)
        except ValueError:
            return SolveResult(False, [], 'ghost.invalid', 0, 0, [])
        stages = [SolveStage('ghost.floppy', 'ghost.floppy', list(moves))]
    else:
        work = cube.clone()
        prefix = work.alignment_moves()
        work.apply_moves(prefix)
        work._solving = True
        if cube.n == 2:
            from solver.solver2 import solve_2x2_facelets
            result = solve_2x2_facelets(cubies_to_facelets(work.cubies, 2), cancel_event=cancel_event)
        elif cube.n == 3:
            from solver.solver3 import solve_3x3
            result = solve_3x3(cubies_to_facelets(work.cubies, 3))
        else:
            from solver.solver_n import solve_nxn
            result = solve_nxn(work, cancel_event=cancel_event, progress_callback=progress_callback)
        if not result.success:
            return result
        work.apply_moves(result.moves)
        body = list(result.moves)
        if cube.n == 3:
            from solver.mastermorphix import center_solution
            if cancelled():
                raise InterruptedError()
            correction = list(center_solution(work.center_twists()))
            work.apply_moves(correction)
            body.extend(correction)
        suffix = work.alignment_moves(restore=True)
        moves = prefix + body + suffix
        stages = ([SolveStage('ghost.align', 'ghost.align', prefix)] if prefix else [])
        stages.append(SolveStage('ghost.body', 'ghost.body', body))
        if suffix:
            stages.append(SolveStage('ghost.restore', 'ghost.restore', suffix))
    replay = cube.clone()
    for token in moves:
        if cancelled():
            raise InterruptedError()
        replay.apply_move(token)
    if not replay.is_solved():
        return SolveResult(False, [], 'ghost.replay_failed', int((perf_counter()-started)*1000), 0, [])
    return SolveResult(True, moves, '', int((perf_counter()-started)*1000), len(moves), stages)
