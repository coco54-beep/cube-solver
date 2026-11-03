"""Twelve-axis cornerless Clover Tetrahedron research material.

This is distinct from both Curvy Hexagram (four intact corners) and the
unrelated three-axis Reuleaux Leaf Tetrahedron. Housing is chordal geometry.
Its truncated body does NOT match the photographed LanLan shell; keep it out
of the public catalogue until the physical cuts and housing are corrected.
"""
import math
from functools import lru_cache
from cube.hexagram import HexagramCube,shell
from cube.pisces import AXES,fields_for
from cube.polyhedral import TETRA,scale,dot
from cube.compound_solids import face_normal
from cube.twins_material import partition

CUT=.481769274602002
TIPS=tuple(scale(n,math.sqrt(3)/2) for n in TETRA)


def contains(solid,point):
    return all(dot(face_normal(poly),point)<=dot(face_normal(poly),poly[0])+1e-8 for poly,color in solid)


@lru_cache(maxsize=1)
def structure():
    cells=(shell(),)
    for n in AXES:cells=partition(cells,n,CUT)
    removed=tuple(c for c in cells if any(contains(c,p) for p in TIPS))
    if len(removed)!=4:raise ValueError('Clover Pyraminx must omit exactly four corner bodies')
    cells=tuple(c for c in cells if c not in removed)
    return cells,fields_for(cells)


@lru_cache(maxsize=1)
def layout():
    cells,panels=structure();return tuple(range(len(cells))),cells,panels


class CloverPyraminxCube(HexagramCube):
    puzzle_kind='lanlan_clover_pyraminx'
    observation_model='lanlan-clover-pyraminx-chordal-v1'
    cut_bounds=(CUT,)*12
    layout=staticmethod(layout)
