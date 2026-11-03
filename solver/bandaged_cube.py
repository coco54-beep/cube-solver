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
    elif not moves and not cube.is_solved() and cube.puzzle_kind in (
            'burr_cube','ai_cube','two_bar_cube','bandaged_c','bicube'):
        from solver.bandaged_reduction import solve_bandage_reduction
        # A 3x3's fixed centre colours determine its global holding. The
        # layout graph is expressed in that canonical frame; undoing the
        # holding uses legal whole-cube turns, never an unconstrained face.
        if cube.n == 3:
            from solver.bandaged_state import canonical_three
            work,prefix=canonical_three(cube,cancelled)
            moves=list(prefix)+solve_bandage_reduction(work,cancelled)
        else:
            moves=solve_bandage_reduction(cube,cancelled)
    if not moves and not cube.is_solved():
        raise ValueError('bandage.state_unreachable')
    # Merge adjacent turns of the same face before the final verification.
    try:
        combined=_combine_bandaged(moves)
        trial=cube.clone();trial.history=[]
        trial.apply_moves(combined)
        if trial.is_solved():moves=combined
    except (ValueError,KeyError):
        pass
    from solver.rigid_word import shorten_rigid_word
    moves=shorten_rigid_word(cube,moves,cancelled)
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
        raise ValueError('bandage.search_replay')
    return moves

def _combine_bandaged(moves):
    from cube.notation import parse_move_full, suffix_for_count
    result = []
    for token in moves:
        try: label, layers, count = parse_move_full(token)
        except (ValueError, KeyError):
            result.append(token); continue
        if result:
            try: prev_label, prev_layers, prev_count = parse_move_full(result[-1])
            except (ValueError, KeyError): prev_label = None
            if prev_label is not None and (label, layers) == (prev_label, prev_layers):
                total = (prev_count + count) % 4
                result.pop()
                if total:
                    prefix = str(layers) if layers > 1 else ''
                    result.append(prefix + label + suffix_for_count(total))
                continue
        result.append(token)
    return result
