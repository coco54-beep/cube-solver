"""Solve geometry-entered mirror states with their ordinary NxN mechanism."""
from functools import lru_cache
from itertools import product


@lru_cache(maxsize=7)
def _center_endings(kind):
    from cube.mastermorphix import AXIS_FACES, IDENTITY
    from cube.coordinates import FACE_NORMALS, TURNS
    from cube.mirror_shape import shell_signature
    choices = []
    for face in AXIS_FACES:
        home = FACE_NORMALS[face]
        target = shell_signature(kind, home)
        frame = IDENTITY
        allowed = []
        for count in range(4):
            if shell_signature(kind, home, frame) == target:
                allowed.append(count)
            frame = tuple(TURNS[face](*v) for v in frame)
        choices.append(allowed)
    return tuple(product(*choices))


def _shape_finish(cube, body, cancelled):
    from solver.mastermorphix import center_solution, _compact_moves
    work = cube.clone()
    work.apply_moves(body)
    twists = work.center_twists()
    best = None
    for ending in _center_endings(cube.shape_kind):
        if cancelled():
            raise InterruptedError()
        delta = tuple((twist - goal) % 4 for twist, goal in zip(twists, ending))
        if sum(delta) % 2:
            continue
        turns = center_solution(delta)
        candidate = _compact_moves(list(body) + list(turns))
        if best is None or len(candidate) < len(best):
            best = candidate
    if best is None:
        raise ValueError('No legal silver centre orientation')
    return best


def _solve_shape(cube, original, cancel_event, budget):
    from time import perf_counter
    from cube.conversion import cubies_to_facelets
    from solver.solver3 import solve_3x3
    from solver.result import SolveResult, SolveStage
    from solver.mastermorphix import _compact_moves
    from cube.mirror_shape import normalize_shape_input, equivalent_shells
    started = perf_counter()
    cancelled = lambda: cancel_event is not None and cancel_event.is_set()
    if cancelled():
        raise InterruptedError()
    if original.is_solved():
        return SolveResult(True, [], '', 0, 0, [])
    body = solve_3x3(cubies_to_facelets(cube.cubies, 3))
    if not body.success:
        return body
    best = _shape_finish(cube, body.moves, cancelled)
    replay = original.clone()
    replay.apply_moves(best)
    if not replay.is_solved():
        return SolveResult(False, [], 'Mirror geometry replay failed', 0, 0, [])
    # Rank the complete shape solution: a shorter ordinary 3x3 solution can
    # otherwise require a much longer silver-centre correction.
    deadline = perf_counter() + max(0, budget)
    seen = set()
    interchangeable = any(
        sum(v != 0 for v in pos) > 1 and
        len(equivalent_shells(cube.shape_kind, piece.home, piece.frame, pos)) > 1
        for pos, piece in cube.cubies.items()) if budget > 0 else False
    # Interleave the existing short-prefix searches with equivalent-label
    # searches. Neither additional method can displace the validated fallback
    # unless its complete shape solution is strictly shorter.
    attempts = (((), 1), ((), 0), (('R',), 0), ((), 2),
                (('U',), 0), ((), 3), (('F',), 0))
    for prefix, preference in attempts:
        if len(best) <= 8 or perf_counter() >= deadline:
            break
        if cancelled():
            raise InterruptedError()
        if preference:
            if not interchangeable:
                continue
            matching_deadline = min(deadline, perf_counter() + .12)
            try:
                trial = normalize_shape_input(
                    cube, lambda: cancelled() or perf_counter() >= matching_deadline,
                    preference=preference)
            except InterruptedError:
                if cancelled():
                    raise
                continue
        else:
            trial = cube.clone()
        trial.apply_moves(prefix)
        marker = tuple((pos, piece.home, piece.frame)
                       for pos, piece in sorted(trial.cubies.items()))
        if marker in seen:
            continue
        seen.add(marker)
        if perf_counter() >= deadline:
            break
        try:
            result = solve_3x3(cubies_to_facelets(trial.cubies, 3), max_length=18,
                               timeout=min(.15, max(.01, deadline - perf_counter())))
        except (ValueError, TimeoutError):
            continue
        if cancelled():
            raise InterruptedError()
        if not result.success:
            continue
        candidate = _compact_moves(list(prefix) + _shape_finish(trial, result.moves, cancelled))
        if len(candidate) >= len(best):
            continue
        replay = original.clone()
        replay.apply_moves(candidate)
        if replay.is_solved():
            best = candidate
    return SolveResult(True, best, '', int((perf_counter() - started) * 1000), len(best),
                       [SolveStage('shape.body_centres', 'shape.body_centres', list(best))])


def solve_mirror(cube,cancel_event=None,progress_callback=None,optimize_budget=.6):
    from time import perf_counter
    started = perf_counter()
    from cube.conversion import cubies_to_facelets
    original = cube
    shaped = getattr(cube, 'shape_kind', None) is not None
    if shaped:
        from cube.mirror_shape import normalize_shape_input
        from cube.mastermorphix import MorphixInputError
        from solver.result import SolveResult
        try:
            cube = normalize_shape_input(cube, lambda: cancel_event is not None and cancel_event.is_set())
        except MorphixInputError as exc:
            return SolveResult(False, [], f'morphix.error.{exc}', 0, 0, [])
        result = _solve_shape(cube, original, cancel_event, optimize_budget)
        result.elapsed_ms = int((perf_counter() - started) * 1000)
        return result
    if cube.n==2:
        from solver.solver2 import solve_2x2_facelets
        result=solve_2x2_facelets(cubies_to_facelets(cube.cubies,2),cancel_event=cancel_event)
    elif cube.n==3:
        from solver.solver3 import solve_3x3
        facelets = cubies_to_facelets(cube.cubies, 3)
        result=solve_3x3(facelets)
        if result.success and len(result.moves) > 18 and optimize_budget > 0:
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError()
            # Keep the original result as fallback; virtual colours are exact
            # solver labels for the mirror's unequal dimensions.
            try:
                candidate = solve_3x3(facelets, max_length=18, timeout=min(.2, optimize_budget))
            except (ValueError, TimeoutError):
                candidate = None
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError()
            if candidate is not None and candidate.success and len(candidate.moves) < len(result.moves):
                check = cube.clone()
                check.apply_moves(candidate.moves)
                if check.is_solved():
                    result = candidate
    else:
        from solver.solver_n import solve_nxn
        result=solve_nxn(cube,cancel_event=cancel_event,progress_callback=progress_callback)
    if result.success:
        replay=cube.clone()
        replay.apply_moves(result.moves)
        if not replay.is_solved():
            from solver.result import SolveResult
            return SolveResult(False,[],'Mirror geometry replay failed',result.elapsed_ms,0,[])
    result.elapsed_ms = int((perf_counter() - started) * 1000)
    return result
