"""Prepared core stabilizers and orbit cycles for Face-Turning Octahedra."""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import Move
from solver.lattice_data import geometry_key
from solver.polyhedral import compose,identify,inverse,inverse_word,piece_orbits,simplify


def core_points(cube):
    g=cube.geometry
    # Diamond's two four-piece centre orbits move too. They must be solved
    # here: the subsequent three-cycle reduction only handles larger orbits.
    return tuple(s for orbit in piece_orbits('fto',cube.n)
                 if len(g.pieces[orbit[0]])==4 or len(orbit)<=6
                 for piece in orbit for s in g.pieces[piece])


@lru_cache(maxsize=1)
def _assets():
    path=Path(__file__).parent/'data'/'fto_core.bin'
    try:
        return json.loads(zlib.decompress(path.read_bytes()))
    except (OSError,ValueError,zlib.error):
        return {}


@lru_cache(maxsize=1)
def _cycle_assets():
    path=Path(__file__).parent/'data'/'fto_cycles.bin'
    try:
        return json.loads(zlib.decompress(path.read_bytes()))
    except (OSError,ValueError,zlib.error):
        return {}


def prepared_cycles(cube,targets):
    record=_cycle_assets().get(str(cube.n))
    if not record or record.get('geometry')!=geometry_key(cube.geometry):
        return None
    try:
        return {index:(tuple(Move(*move) for move in record['cycles'][str(index)]['word']),
                       tuple(record['cycles'][str(index)]['base'])) for index in targets}
    except (KeyError,TypeError,ValueError):
        return None


def solve_prepared_core(cube,cancel=None,progress=None):
    """Return a core word, or None if this geometry needs runtime preparation."""
    record=_assets().get(str(cube.n))
    points=core_points(cube)
    if not record or record['geometry']!=geometry_key(cube.geometry) or tuple(record['points'])!=points:
        return None
    indices={s:i for i,s in enumerate(points)}
    full=identify(cube)
    state=tuple(indices[full[s]] for s in points)
    identity=tuple(range(len(points)))
    solution=[]
    rows=record['rows']
    for k in range(len(points)-1,-1,-1):
        if cancel and cancel():
            raise InterruptedError()
        j=state[k]
        if j!=k:
            entry=rows[k].get(str(j))
            if entry is None:
                raise ValueError('The entered puzzle is not a legal state')
            permutation,word=entry
            state=compose(state,inverse(permutation))
            solution.extend(inverse_word(tuple(Move(*m) for m in word),3))
        if progress:
            progress(len(points)-k,len(points))
    if state!=identity:
        raise ValueError('The entered puzzle is not a legal state')
    return simplify(solution,3)
