"""Solve entered Flower Dodecahedron colours using regular edge half turns."""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import Move
from solver.lattice_data import geometry_key
from solver.polyhedral import identify, piece_orbits, simplify, _parity
from solver.polyhedral_reduction import Transports, orbit_word


@lru_cache(maxsize=4)
def _assets(kind='blossom'):
    path = Path(__file__).parent / 'data' / (kind + '_cycles.bin')
    return json.loads(zlib.decompress(path.read_bytes()))


def solve_blossom(cube, cancel=None, progress=None):
    """Orient fixed-position edge caps, then independently reduce six orbits.

    Each prepared macro fixes every sticker outside its ten-petal orbit.
    The conjugating turns cancel too, including their edge-cap flips.
    """
    return _solve_edge_petals(cube, _assets(), cancel, progress)


@lru_cache(maxsize=1)
def _short_petal_macros():
    """Use the six-move no-centre macros for petals, centres last.

    The no-centre word cycles three petals and three centres. Petals solve
    first; the final ten-move centre macro fixes every petal again.
    """
    from cube.polyhedral import PolyhedralPuzzle
    full = PolyhedralPuzzle.solved('petal_icosahedron', 3)
    full.colors = [s.face for s in full.geometry.stickers]
    g = full.geometry
    orbits = piece_orbits('petal_icosahedron', 3)
    centre = max(range(len(orbits)), key=lambda i: len(orbits[i]))
    full_record = _assets('petal_icosahedron')
    short_record = _assets('petal_icosahedron_nocentre')
    macros = {}
    for key, macro in short_record['cycles'].items():
        work = full.clone()
        for move in macro['word']:
            work.apply_move(Move(*move))
        state = identify(work)
        changed = sorted({g.stickers[i].piece for i, (a, b) in
                          enumerate(zip(work.colors, full.colors)) if a != b})
        petals = [piece for piece in changed if piece not in set(orbits[centre])]
        if len(petals) != 3:
            raise ValueError('Petal short macro is not an isolated petal cycle')
        position = {piece: g.stickers[state[g.pieces[piece][0]]].piece
                    for piece in petals}
        first = petals[0]
        second = position[first]
        third = position[second]
        if position[third] != first:
            raise ValueError('Petal short macro has an unexpected cycle')
        index = next(i for i, orbit in enumerate(orbits)
                     if set(petals) <= set(orbit))
        macros[index] = (tuple(Move(*move) for move in macro['word']),
                         (first, second, third))
    record = full_record['cycles'][str(centre)]
    centre_macro = (tuple(Move(*move) for move in record['word']),
                    tuple(record['base']))
    return macros, centre, centre_macro


def _solve_petal_icosahedron_short(cube, cancel, progress):
    macros, centre, centre_macro = _short_petal_macros()
    work = cube.entered()
    g = work.geometry
    orbits = piece_orbits('petal_icosahedron', 3)
    targets = {i: orbit for i, orbit in enumerate(orbits) if len(orbit) > 1}
    if set(macros) != set(targets) - {centre}:
        raise ValueError('Petal short macros do not cover every petal orbit')
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
        first = g.pieces[cap][0]
        if work.colors[first] != g.stickers[first].face:
            execute((Move(axis),))

    order = [index for index in targets if index != centre] + [centre]
    for stage, index in enumerate(order):
        if cancel and cancel():
            raise InterruptedError()
        if progress:
            progress(stage, len(order))
        orbit = targets[index]
        labels = identify(work)
        ids = {piece: i for i, piece in enumerate(orbit)}
        destination = [None] * len(orbit)
        for home in orbit:
            position = g.stickers[labels[g.pieces[home][0]]].piece
            destination[ids[position]] = ids[home]
        primitive, base = centre_macro if index == centre else macros[index]
        transports = Transports(work, orbit, base, cancel, both_directions=True)
        execute(orbit_word(transports, orbit, destination, primitive, solution))
    if not work.is_solved():
        raise ValueError('Petal short reduction replay failed')
    return simplify(solution, 2)


def solve_petal_icosahedron(cube, cancel=None, progress=None):
    """Solve six petal orbits, the movable centre orbit and edge-cap flips."""
    if cube.puzzle_kind == 'petal_icosahedron':
        try:
            return _solve_petal_icosahedron_short(cube, cancel, progress)
        except (ValueError, KeyError):
            pass
    return _solve_edge_petals(cube, _assets(cube.puzzle_kind), cancel, progress)


def _solve_edge_petals(cube, record, cancel, progress):
    if cancel and cancel():
        raise InterruptedError()
    work = cube.entered()
    g = work.geometry
    orbits = piece_orbits(cube.puzzle_kind, cube.n)
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
