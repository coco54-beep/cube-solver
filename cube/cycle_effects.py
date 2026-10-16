"""Exact three-piece effects shared by tutorials and optional solver finishes."""
from functools import lru_cache


@lru_cache(maxsize=256)
def three_cycle(kind, order, word):
    from cube.polyhedral import geometry
    g = geometry(kind, order)
    permutation = tuple(range(len(g.stickers)))
    for move in word:
        action = g.permutation(move)
        permutation = tuple(action[i] for i in permutation)
    affected = {g.stickers[i].piece for i, target in enumerate(permutation) if target != i}
    if len(affected) != 3:
        return None
    destinations = {}
    for piece in affected:
        landing = {g.stickers[permutation[i]].piece for i in g.pieces[piece]}
        if len(landing) != 1:
            return None
        destinations[piece] = landing.pop()
    if set(destinations.values()) != affected or any(p == d for p, d in destinations.items()):
        return None
    if any(permutation[permutation[permutation[i]]] != i for i in range(len(permutation))):
        return None
    # Same-colour center cycles can be mechanically real but invisible to a
    # learner. They do not make useful colour-entry cases or visible finishes.
    if not any(g.stickers[i].face != g.stickers[target].face for i, target in enumerate(permutation)):
        return None
    return tuple(sorted(destinations.items())), permutation
