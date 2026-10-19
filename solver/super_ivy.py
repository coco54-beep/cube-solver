"""Prepared, geometry-bound three-cycles for painted Super Ivy input."""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import Move
from solver.lattice_data import geometry_key


@lru_cache(maxsize=1)
def prepared():
    return json.loads(zlib.decompress(
        (Path(__file__).parent / 'data/super_ivy_cycles.bin').read_bytes()))


def prepared_cycles(cube, targets):
    record = prepared()
    if record['geometry'] != geometry_key(cube.geometry):
        raise ValueError('Super Ivy formula data does not match the model')
    return {i: (tuple(Move(*m) for m in record['cycles'][str(i)]['word']),
                tuple(record['cycles'][str(i)]['base'])) for i in targets}


def solve_super_ivy(cube, cancel=None, progress=None):
    """Edges, centres, then both leaf orbits; preserve each finished stage.

    A native edge cycle costs one turn. Solving it first avoids the forty
    turns needed to move edges while preserving every leaf and centre.
    """
    from solver.polyhedral import identify, piece_orbits, simplify
    from solver.polyhedral_reduction import Transports, orbit_word
    record = prepared()
    work = cube.entered()
    g = work.geometry
    if record['geometry'] != geometry_key(g):
        raise ValueError('Super Ivy formula data does not match the model')
    identify(work)
    orbits = piece_orbits('super_ivy', 3)
    solution = []
    for stage, index in enumerate(record['order']):
        if cancel and cancel():
            raise InterruptedError()
        if progress:
            progress(stage, len(orbits))
        orbit = orbits[index]
        state = identify(work, only={index})
        positions = {piece: i for i, piece in enumerate(orbit)}
        destination = [None] * len(orbit)
        for home in orbit:
            pos = g.stickers[state[g.pieces[home][0]]].piece
            destination[positions[pos]] = positions[home]
        if destination == list(range(len(orbit))):
            continue
        macro = record['staged'][str(index)]
        primitive = tuple(Move(*m) for m in macro['word'])
        transport = Transports(work, orbit, tuple(macro['base']), cancel,
                               both_directions=True)
        word = orbit_word(transport, orbit, destination, primitive, solution,
                          alternatives=len(g.pieces[orbit[0]]) == 1,
                          search_budget=.04)
        for move in word:
            if cancel and cancel():
                raise InterruptedError()
            work.apply_move(move)
        solution.extend(word)
    if not work.is_solved():
        raise ValueError('Super Ivy solution replay failed')
    if progress:
        progress(len(orbits), len(orbits))
    return simplify(solution, g.spec.turn_order)
