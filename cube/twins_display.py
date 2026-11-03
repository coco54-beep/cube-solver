"""Drawing3 exterior bound to the independent pCubes material identities.

These cached display surfaces are never used for collision or move legality.
The reference's full material remains the mechanism, including hidden bodies.
"""
import json,zlib
from functools import lru_cache
from pathlib import Path
from cube.twins_pcubes import fingerprint
from cube.twins_cad_material import fingerprint as cad_fingerprint


@lru_cache(maxsize=1)
def data():
    value=json.loads(zlib.decompress((Path(__file__).parent/'data/twins_pcubes_skin.bin').read_bytes()))
    if (value.get('version')!=1 or value.get('source')!=fingerprint() or
            value.get('cad_source')!=cad_fingerprint()):
        raise ValueError('Stale Twins curved reference skin')
    return value


@lru_cache(maxsize=1)
def panels():
    return tuple((h,f,tuple(tuple(p) for p in poly)) for h,f,poly in data()['panels'])


@lru_cache(maxsize=1)
def surfaces():
    return tuple(tuple((tuple(tuple(p) for p in t),tuple(n),slot) for t,n,slot in row)
                 for row in data()['surfaces'])
