"""Small, bounded facelet search before high-order Pyraminx reduction."""
from functools import lru_cache
from time import monotonic

from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import inverse_word, simplify


@lru_cache(maxsize=1)
def _short_model():
    cube = PolyhedralPuzzle.solved('pyraminx', 5)
    g = cube.geometry
    goal = bytes(cube.colors)
    actions = []
    seen = set()
    for move in cube.moves():
        for atom in (move, move.inverse(g.spec.turn_order)):
            permutation = g.inverse_permutation(atom)
            if permutation not in seen:
                seen.add(permutation)
                actions.append((atom, permutation))
    # Two layers from solved, bounded independently of the number of moves.
    limit = min(2048, max(64, 1024 * 1024 // (len(goal) + 256)))
    table = {goal: ()}
    frontier = [goal]
    for _ in range(2):
        following = []
        for state in frontier:
            word = table[state]
            for move, permutation in actions:
                after = bytes(map(state.__getitem__, permutation))
                if after not in table:
                    table[after] = word + (move,)
                    following.append(after)
                    if len(table) >= limit:
                        return tuple(actions), table
        frontier = following
    return tuple(actions), table


def short_solution(cube, cancel=None, budget=.08):
    """Return a replayed short solution, or None for the normal reduction."""
    if cancel and cancel():
        raise InterruptedError()
    actions, table = _short_model()
    started = monotonic()
    state = bytes(cube.colors)
    visited = {state}
    frontier = [(state, ())]
    best = None
    count = 0
    for depth in range(3):
        following = []
        for state, prefix in frontier:
            count += 1
            if count % 32 == 0:
                if cancel and cancel():
                    raise InterruptedError()
                if monotonic() - started >= budget:
                    return _validated(cube, best, cancel)
            ending = table.get(state)
            if ending is not None:
                word = simplify(prefix + inverse_word(ending, 3), 3)
                if best is None or len(word) < len(best):
                    best = word
            if depth == 2:
                continue
            for move, permutation in actions:
                if prefix and (move.axis, move.layer) == (prefix[-1].axis, prefix[-1].layer):
                    continue
                after = bytes(map(state.__getitem__, permutation))
                if after not in visited:
                    visited.add(after)
                    following.append((after, prefix + (move,)))
                    if len(visited) >= 2048:
                        return _validated(cube, best, cancel)
        frontier = following
    return _validated(cube, best, cancel)


def _validated(cube, word, cancel):
    if word is None:
        return None
    replay = cube.entered()
    for move in word:
        if cancel and cancel():
            raise InterruptedError()
        replay.apply_move(move)
    return word if replay.is_solved() else None
