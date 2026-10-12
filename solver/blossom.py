"""Solve entered Flower Dodecahedron colours using regular edge half turns."""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import Move
from solver.lattice_data import geometry_key
from solver.polyhedral import identify, piece_orbits, simplify, _parity
from solver.polyhedral_reduction import Transports, orbit_word


@lru_cache(maxsize=1)
def _assets():
    path = Path(__file__).parent / 'data' / 'blossom_cycles.bin'
    return json.loads(zlib.decompress(path.read_bytes()))


def solve_blossom(cube, cancel=None, progress=None):
    """Orient fixed-position edge caps, then independently reduce six orbits.

    Each prepared macro fixes every sticker outside its ten-petal orbit.
    The conjugating turns cancel too, including their edge-cap flips.
    """
    if cancel and cancel():
        raise InterruptedError()
    work = cube.entered()
    g = work.geometry
    record = _assets()
    orbits = piece_orbits('blossom', 3)
    targets = {i: orbit for i, orbit in enumerate(orbits) if len(orbit) > 1}
    if record['geometry'] != geometry_key(g) or set(record['cycles']) != {
            str(i) for i in targets}:
        raise ValueError('The Blossom solver assets do not match this model')
    identify(work)
    solution = []

    def execute(word):
        for move in word:
            if cancel and cancel():
                raise InterruptedError()
            work.apply_move(move)
        solution.extend(word)

    for axis, layers in enumerate(g.layers):
        cap = next(piece for piece in layers[0] if len(g.pieces[piece]) == 2)
        a = g.pieces[cap][0]
        if work.colors[a] != g.stickers[a].face:
            execute((Move(axis),))

    for stage, (index, orbit) in enumerate(targets.items()):
        if cancel and cancel():
            raise InterruptedError()
        if progress:
            progress(stage, len(targets))
        labels = identify(work)
        ids = {piece: i for i, piece in enumerate(orbit)}
        destination = [None] * len(orbit)
        for home in orbit:
            position = g.stickers[labels[g.pieces[home][0]]].piece
            destination[ids[position]] = ids[home]
        if _parity(destination):
            raise ValueError('The entered puzzle is not a legal state')
        macro = record['cycles'][str(index)]
        primitive = tuple(Move(*move) for move in macro['word'])
        transports = Transports(work, orbit, tuple(macro['base']), cancel, both_directions=True)
        execute(orbit_word(transports, orbit, destination, primitive, solution))
    if not work.is_solved():
        raise ValueError('Blossom reduction replay failed')
    if progress:
        progress(len(targets), len(targets))
    return simplify(solution, 2)
