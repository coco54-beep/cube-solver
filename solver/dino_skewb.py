"""Prepared formulas for the TomZ Dino Skewb, with model fingerprint checks."""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import Move
from solver.lattice_data import geometry_key


@lru_cache(maxsize=2)
def prepared(kind='dino_skewb'):
    if kind not in ('dino_skewb','dayan_dino_skewb'):
        raise ValueError('Unsupported Dino Skewb variant')
    return json.loads(zlib.decompress(
        (Path(__file__).parent/'data'/f'{kind}_cycles.bin').read_bytes()))


def prepared_cycles(cube,targets):
    record=prepared(cube.puzzle_kind)
    if record['geometry']!=geometry_key(cube.geometry):
        raise ValueError('Dino Skewb formulas do not match this model')
    return {i:(tuple(Move(*m) for m in record['cycles'][str(i)]['word']),
               tuple(record['cycles'][str(i)]['base'])) for i in targets}
