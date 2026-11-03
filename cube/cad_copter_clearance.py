"""Whole CAD solids against invariant turn cuts, including invisible material.

A turn moves only solids wholly inside its sphere/halfspace. Rotation about
the cut axis preserves that region throughout the motion, so the stationary
outside solids cannot be crossed. Twins solids are unions of arrangement
atoms; an atom is never mistaken for a separately movable piece.
"""
import math
from functools import lru_cache
from cube.polyhedral import CUBE,scale
from cube.curved_partition import SphereCut
from cube.spherical_cells import Arrangement,Plane


@lru_cache(maxsize=2)
def regions(kind):
    if kind=='flower':
        from cube.flower_material import cuts,structure
        arrangement=Arrangement(tuple(Plane(n,1.) for n in CUBE),cuts())
        return tuple((arrangement.region(mask),) for mask in structure()[0])
    from cube.twins_cad_material import cuts,structure,data,group
    arrangement=Arrangement(tuple(Plane(n,1.) for n in CUBE),cuts())
    atoms={g:[] for g in structure()[0]}
    for mask in data()['atoms']:atoms[group(mask)].append(arrangement.region(mask))
    return tuple(tuple(atoms[g]) for g in structure()[0])


@lru_cache(maxsize=32768)
def side(kind,home,cut):
    if kind=='flower':
        from cube.flower_material import cuts,structure
        mask=structure()[0][home]
    else:
        from cube.twins_cad_material import cuts,data,group,structure
        g=structure()[0][home]
        # All atoms share an active edge or diagonal bit. Ignored conditional
        # Cartesian/radial cuts must still be tested on the complete union.
        mask=None
        for axis,c in enumerate(cuts()):
            sign=matching_cut(c,cut)
            if sign and axis<16:
                bits=g[0] if axis<12 else g[1];index=axis if axis<12 else axis-12
                return (1 if bits&(1<<index) else -1)*sign
    if mask is not None:
        for axis,c in enumerate(cuts()):
            sign=matching_cut(c,cut)
            if sign:return (1 if mask&(1<<axis) else -1)*sign
    result=None
    for atom in regions(kind)[home]:
        value=atom.side(cut)
        if value==0 or result is not None and result!=value:return 0
        result=value
    return result


def matching_cut(a,b):
    if isinstance(a,Plane) and isinstance(b,Plane):
        if abs(a.bound-b.bound)<1e-9 and math.dist(a.normal,b.normal)<1e-8:return 1
        if abs(a.bound+b.bound)<1e-9 and math.dist(a.normal,scale(b.normal,-1))<1e-8:return -1
    elif isinstance(a,SphereCut) and isinstance(b,SphereCut):
        if abs(a.radius-b.radius)<1e-9 and math.dist(a.centre,b.centre)<1e-8:return 1
    return 0


def local_cut(frame,cut):
    from cube.curvy_copter import inverse_point
    if isinstance(cut,Plane):return Plane(tuple(round(v,10) for v in inverse_point(frame,cut.normal)),cut.bound)
    return SphereCut(tuple(round(v,10) for v in inverse_point(frame,cut.centre)),cut.radius)
