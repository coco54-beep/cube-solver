"""Unpublished regular-turn study of MF8 Twins' split edge caps.

The cubic model has six independent parts at every edge. Coordinate cuts
split the two-colour carrier, but are not additional 2x2 turning axes.
Half-Skewb positions, partial edge turns and jumbling gates are NOT modelled.
This module is deliberately not a playable catalogue entry.
"""
from cube.polyhedral import (CUBE, EDGE_AXES, OCTA, TETRA, Spec, _clover_skin,
                             clip, scale)


def specification():
    return Spec('twins', 3, CUBE, EDGE_AXES + OCTA, (), 6,
                axis_steps=(3,)*12 + (2,)*8)


def skin(spec):
    fragments=[]
    for source, face, polygon in _clover_skin(spec):
        cells=[((),polygon)]
        for axis in TETRA + ((1.,0.,0.),(0.,1.,0.),(0.,0.,1.)):
            split=[]
            for signature, part in cells:
                for sign in (-1,1):
                    result=clip(part,scale(axis,-sign),0.)
                    if result:split.append((signature+(sign,),result))
            cells=split
        fragments.extend(((source,signature),face,part) for signature,part in cells)
    return fragments
