"""Twelve-axis Curvy Hexagram with its own rounded tetrahedral housing.

The stored chordal shell approximates a four-ball Reuleaux tetrahedron; it
does not substitute a three-axis leaf tetrahedron or a straight Pyraminx.
"""
import json,zlib
from pathlib import Path
from functools import lru_cache
from cube.pisces import PiscesCube,AXES,fields_for
from cube.planar_twins_state import RecordedTurns
from cube.polyhedral import TETRA,scale
from cube.twins_material import partition

CUT=.49
NORMALS=tuple(scale(n,-1) for n in TETRA)


@lru_cache(maxsize=1)
def shell():
    data=json.loads(zlib.decompress((Path(__file__).parent/'data/pillowed_tetra_shell.bin').read_bytes()))
    if data.get('version')!=1 or data.get('model')!='four-ball-reuleaux-tetrahedron':raise ValueError('Invalid rounded tetrahedron mesh')
    return tuple((tuple(tuple(p) for p in poly),color) for poly,color in data['faces'])


@lru_cache(maxsize=1)
def structure():
    cells=(shell(),)
    for n in AXES:cells=partition(cells,n,CUT)
    return tuple(cells),fields_for(cells)


@lru_cache(maxsize=1)
def layout():
    solids,panels=structure();return tuple(range(len(solids))),solids,panels


class HexagramCube(RecordedTurns, PiscesCube):
    puzzle_kind='lanlan_hexagram'
    color_count=4
    geometry_profile='chordal-reuleaux-tetrahedron'
    observation_model='lanlan-hexagram-chordal-v1'
    cut_bounds=(CUT,)*12
    layout=staticmethod(layout)
    face_normals=NORMALS
