"""Core-preserving actions on the free extensions, with offline phase tables."""
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from collections import defaultdict
import json
import zlib
import math
import hashlib

from cube.polyhedral import Move
from solver.polyhedral import compose, inverse, inverse_word


@lru_cache(maxsize=1)
def extension_mechanism(kind):
    payload = (Path(__file__).parent/'data'/f'{kind}_extensions.bin').read_bytes()
    if payload[:4] != b'CE01':
        raise ValueError('Invalid extension macro version')
    data = json.loads(zlib.decompress(payload[4:]))
    if data['kind'] != kind:
        raise ValueError('Wrong extension macro model')
    original = tuple(tuple(p) for p in data['panels'])
    permutations = [tuple(r['permutation']) for r in data['records']]
    words = [tuple(Move(*m) for m in r['word']) for r in data['records']]
    by_piece = defaultdict(list)
    for i, (p, f) in enumerate(original):
        by_piece[p].append(i)
    piece_at = {i: p for p, slots in by_piece.items() for i in slots}
    neighbours = {p: {piece_at[perm[slots[0]]] for perm in permutations} for p, slots in by_piece.items()}
    left = set(by_piece); orbits = []
    while left:
        found = {min(left)}; todo = list(found)
        while todo:
            for p in neighbours[todo.pop()]-found:
                found.add(p); todo.append(p)
        left -= found; orbits.append(tuple(sorted(found)))
    orbits.sort(key=lambda orbit: (-len(by_piece[orbit[0]]), orbit))
    panels = tuple(original[i] for orbit in reversed(orbits) for p in orbit for i in by_piece[p])
    old_to_new = {original.index(p): i for i, p in enumerate(panels)}
    maps = []; orders = []
    for a, perm in enumerate(permutations):
        perm = tuple(old_to_new[perm[original.index(p)]] for p in panels)
        maps.append(perm); seen = set(); order = 1
        for point in range(len(perm)):
            if point in seen:
                continue
            length = 0; p = point
            while p not in seen:
                seen.add(p); length += 1; p = perm[p]
            order = math.lcm(order, length)
        orders.append(order)
    period = math.lcm(*orders)
    @lru_cache(maxsize=1024)
    def permutation(move):
        count = move.amount % orders[move.axis]
        result = tuple(range(len(panels))); action = maps[move.axis]
        while count:
            if count & 1:
                result = compose(result, action)
            action = compose(action, action); count >>= 1
        return result
    phases = tuple(tuple(i for i, (p, f) in enumerate(panels) if p in orbit) for orbit in orbits)
    geometry = SimpleNamespace(stickers=panels, permutation=permutation, spec=SimpleNamespace(turn_order=period))
    adapter = SimpleNamespace(geometry=geometry, moves=lambda: tuple(Move(a, 0, 1) for a in range(len(words))),
                              phase_points=phases, words=words, orders=orders,
                              fingerprint=hashlib.sha256(payload).hexdigest())
    return adapter, panels, (), {}


def expand(kind, word):
    adapter = extension_mechanism(kind)[0]; bank = adapter.words
    result = []
    for m in word:
        count = m.amount % adapter.orders[m.axis]
        if count > adapter.orders[m.axis]//2:
            result.extend(inverse_word(bank[m.axis], 4)*(adapter.orders[m.axis]-count))
        else:
            result.extend(bank[m.axis]*count)
    return tuple(result)
