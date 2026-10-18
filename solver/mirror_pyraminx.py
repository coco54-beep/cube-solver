"""Solve all oriented mirror Pyraminx pieces, including single-panel centres."""
from collections import OrderedDict

from cube.mirror_pyraminx import marker_system
from solver.polyhedral import StabilizerChain, simplify

_CHAINS = OrderedDict()


def solve_mirror_pyraminx(cube, cancel=None, progress=None):
    return solve_oriented_mirror(cube, cancel, progress)


def solve_oriented_mirror(cube, cancel=None, progress=None):
    if cancel and cancel():
        raise InterruptedError()
    state = cube.labeled_state()
    if cube.is_solved():
        return ()
    # Restore the ordinary mechanism first. Often this restores the complete
    # mirror too; otherwise the marker stage resolves the remaining directions.
    from solver.polyhedral import solve_polyhedral
    prefix = tuple(solve_polyhedral(cube.ordinary_state(), cancel, progress))
    residual = cube.clone()
    for move in prefix:
        if cancel and cancel():
            raise InterruptedError()
        residual.apply_move(move)
    if residual.is_solved():
        return prefix
    state = residual.labeled_state()
    _, _, virtual = marker_system(cube.n, cube.mechanism_kind)
    class Markers:
        geometry = virtual
        def moves(self):
            return cube.moves()
    cache_key = (cube.mechanism_kind, cube.n)
    chain = _CHAINS.get(cache_key)
    if chain is None:
        # Retain one order at a time; do not accumulate oriented group tables
        # when the user switches between the two models on Android.
        _CHAINS.clear()
        chain = StabilizerChain(Markers(), cancel, progress)
        chain.cancel = chain.progress = None
        _CHAINS[cache_key] = chain
    chain.cancel, chain.progress = cancel, progress
    try:
        word = chain.solve(state)
        solution = prefix
        chunk = []
        for move in word.flatten(3, cancel):
            chunk.append(move)
            if len(chunk) == 256:
                solution = simplify(solution + tuple(chunk), 3)
                chunk.clear()
                if len(solution) > 50000:
                    raise ValueError('Oriented mirror solution exceeds the playback limit')
        solution = simplify(solution + tuple(chunk), 3)
        replay = cube.clone()
        for index, move in enumerate(solution):
            if index % 64 == 0 and cancel and cancel():
                raise InterruptedError()
            replay.apply_move(move)
        if not replay.is_solved():
            raise ValueError('Oriented mirror shape replay failed')
        return solution
    finally:
        # Cached chains must not retain a finished screen or cancellation job.
        chain.cancel = chain.progress = None
