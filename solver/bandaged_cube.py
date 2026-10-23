"""History and verified state solutions for rigid cube bandages."""

from cube.bandaged_cube import BandagedCube


def solve_bandaged_cube(cube, cancelled=None):
    if not isinstance(cube, BandagedCube):
        raise TypeError('Expected a bandaged cube')
    if cancelled is not None and cancelled():
        raise InterruptedError()
    moves = cube.solution_from_history()
    if not moves and not cube.is_solved() and cube.puzzle_kind=='fused_cube':
        from solver.bandaged_state import solve_fused
        moves=solve_fused(cube,cancelled)
    elif not moves and not cube.is_solved() and cube.puzzle_kind in ('ai_cube','burr_cube'):
        from solver.bandaged_state import solve_bandaged_state
        moves=solve_bandaged_state(cube,cancelled)
    if not moves and not cube.is_solved() and cube.n == 3:
        from solver.bandaged_search import solve_bandaged_search
        try:
            moves = solve_bandaged_search(cube, cancelled)
        except ValueError:
            moves = []
    if not moves and not cube.is_solved():
        # For a manually entered state, try the corresponding ordinary cube
        # solver and accept its result only when every move is legal for this
        # bandage layout and the full state replays to solved.
        from cube.conversion import cubies_to_facelets
        if cube.n == 3:
            from solver.solver3 import solve_3x3
            result = solve_3x3(cubies_to_facelets(cube.cubies, 3))
        else:
            from solver.solver4 import solve_4x4
            class _CancelEvent:
                def is_set(self):
                    return bool(cancelled and cancelled())

            result = solve_4x4(cube, cancel_event=_CancelEvent())
        if not result.success:
            raise ValueError(result.message or 'The bandaged position is not solved')
        moves = list(result.moves)
    replay = cube.clone()
    replay.history = []
    # Rewind to the canonical solved state, verifying every step obeys the
    # same bandage constraints. This avoids returning a normal-cube solution
    # that would split one of the glued blocks.
    for move in moves:
        if cancelled is not None and cancelled():
            raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError('The current position has no retained legal scramble path')
    return moves
