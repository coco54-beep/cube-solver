"""Prepared three-cycles for Mosaic/Fadi and the asymmetric Tins Cube."""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import Move
from solver.lattice_data import geometry_key


@lru_cache(maxsize=2)
def prepared(kind):
    if kind not in ('mosaic','tins'):
        raise ValueError('Unsupported corner-turning model')
    return json.loads(zlib.decompress(
        (Path(__file__).parent/'data'/f'{kind}_cycles.bin').read_bytes()))


def prepared_cycles(cube,targets):
    record=prepared(cube.puzzle_kind)
    if record['geometry']!=geometry_key(cube.geometry):
        raise ValueError('Mosaic/Tins formulas do not match the model')
    return {i:(tuple(Move(*m) for m in record['cycles'][str(i)]['word']),
               tuple(record['cycles'][str(i)]['base'])) for i in targets}
