"""Exact shortest solutions for all 324 ordinary Pyraminx Duo states."""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import Move, geometry
from solver.lattice_data import geometry_key


@lru_cache(maxsize=1)
def prepared():
    data=json.loads(zlib.decompress((Path(__file__).parent/'data/pyraminx_duo.bin').read_bytes()))
    if data['geometry']!=geometry_key(geometry('pyraminx_duo',3)):
        raise ValueError('Pyraminx Duo formulas do not match its mechanism')
    return data['solutions']


def solve_pyraminx_duo(cube,cancel=None,progress=None):
    if cancel and cancel(): raise InterruptedError()
    if any(type(c) is not int or not 0<=c<4 for c in cube.colors):
        raise ValueError('The entered puzzle is not a legal state')
    atoms=prepared().get(''.join(map(str,cube.colors)))
    if atoms is None: raise ValueError('The entered puzzle is not a legal state')
    solution=tuple(Move(*atom) for atom in atoms)
    replay=cube.entered()
    for move in solution:
        if cancel and cancel(): raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved(): raise ValueError('Pyraminx Duo solution replay failed')
    if progress: progress(len(solution),len(solution))
    return solution
