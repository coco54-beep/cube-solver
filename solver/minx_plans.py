"""Load offline-certified high-minx orbit plans, with runtime fallback."""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import Move
from solver.lattice_data import geometry_key


@lru_cache(maxsize=1)
def _assets():
    try:
        return json.loads(zlib.decompress((Path(__file__).parent/'data/minx_orbit_plans.bin').read_bytes()))
    except (OSError,ValueError,zlib.error):
        return {}


def orbit_plan(cube,targets):
    record=_assets().get(str(cube.n))
    if not record or record.get('geometry')!=geometry_key(cube.geometry):
        return None
    try:
        order=tuple(record['order'])
        staged=record['staged']
        if not isinstance(staged,bool):
            return None
        if set(order)!=set(targets) or len(order)!=len(targets):
            return None
        macros={i:(tuple(Move(*m) for m in record['macros'][str(i)]['word']),
                   tuple(record['macros'][str(i)]['base'])) for i in order}
        if any(not set(base).issubset(targets[i]) for i,(_,base) in macros.items()):
            return None
        return macros,order,staged
    except (KeyError,TypeError,ValueError):
        return None


def core_orbit_plan(cube,targets):
    """Prepared centre plan that protects the already-solved minx core."""
    record=_assets().get(str(cube.n))
    if not record or record.get('geometry')!=geometry_key(cube.geometry):
        return None
    try:
        plan=record['core_plan']
        order=tuple(plan['order'])
        staged=plan['staged']
        if not isinstance(staged,bool) or set(order)!=set(targets) or len(order)!=len(targets):
            return None
        macros={i:(tuple(Move(*m) for m in plan['macros'][str(i)]['word']),
                   tuple(plan['macros'][str(i)]['base'])) for i in order}
        if any(len(base)!=3 or len(set(base))!=3 or not set(base).issubset(targets[i])
               for i,(_,base) in macros.items()):
            return None
        return macros,order,staged
    except (KeyError,TypeError,ValueError):
        return None
