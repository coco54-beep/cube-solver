"""Solve entered colours of the user-confirmed regular edge-turn tetrahedron.

Its petal/centre permutations are coupled. Exact stabilizer tables retain those
constraints instead of assuming that each orbit admits independent 3-cycles.
"""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import Move
from solver.lattice_data import geometry_key
from solver.polyhedral import compose, identify, inverse, inverse_word, simplify


@lru_cache(maxsize=2)
def prepared(kind='petal_tetrahedron'):
    if kind not in ('petal_tetrahedron', 'petal_tetrahedron_nocentre'):
        raise ValueError('Unsupported edge-turn tetrahedron variant')
    path = Path(__file__).parent / 'data' / (kind + '_chain.bin')
    return json.loads(zlib.decompress(path.read_bytes()))


def solve_petal_tetrahedron(cube, cancel=None, progress=None):
    if cancel and cancel():
        raise InterruptedError()
    record = prepared(cube.puzzle_kind)
    if record['geometry'] != geometry_key(cube.geometry):
        raise ValueError('Petal tetrahedron solver data do not match its geometry')
    state = identify(cube)
    word = []
    stages = record['stages']
    for k in range(len(state)-1, -1, -1):
        if cancel and cancel():
            raise InterruptedError()
        if state[k] != k:
            entry = stages[k].get(str(state[k]))
            if entry is None:
                raise ValueError('The entered pieces violate the tetrahedron turn constraints')
            state = compose(state, inverse(tuple(entry['permutation'])))
            word.extend(inverse_word(tuple(Move(*m) for m in entry['word']), 2))
        if progress:
            progress(len(state)-k, len(state))
    if state != tuple(range(len(state))):
        raise ValueError('The entered puzzle is not a legal state')
    solution = simplify(word, 2)
    check = cube.entered()
    for move in solution:
        if cancel and cancel():
            raise InterruptedError()
        check.apply_move(move)
    if not check.is_solved():
        raise ValueError('Petal tetrahedron solution replay failed')
    return solution
