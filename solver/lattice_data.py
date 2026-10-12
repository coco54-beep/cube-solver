"""Load exact three-cycle words bundled for the 4/6 Lattice geometries."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import struct

from cube.polyhedral import Move


def geometry_key(g):
    digest=hashlib.sha256()
    digest.update(repr((g.spec.cuts,g.pieces)).encode('ascii'))
    if g.spec.axis_steps:
        digest.update(repr((g.spec.axis_steps,g.spec.axis_cuts,g.spec.bounds)).encode('ascii'))
    for axis in g.permutations:
        for permutation in axis:
            digest.update(struct.pack('<'+len(permutation)*'H',*permutation))
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _data():
    try:
        return json.loads((Path(__file__).parent/'data'/'lattice_cycles.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):
        return {}


def primitives_for(cube,targets):
    if cube.puzzle_kind!='dino' or cube.n not in (4,6):
        return None
    record=_data().get(str(cube.n))
    if record is None or record.get('geometry')!=geometry_key(cube.geometry):
        return None
    try:
        return {index:(tuple(Move(*move) for move in record['cycles'][str(index)]['word']),
                       tuple(record['cycles'][str(index)]['base'])) for index in targets}
    except (KeyError,TypeError,ValueError):
        return None
