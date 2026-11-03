"""Lee Tutt's seven-axis shallow-cut prism, in two to five layers.

The pentagonal caps turn by 72 degrees; the five side axes turn by 180
degrees. The Professor has a second side cut, matching its five-column
side faces rather than merely making the three-layer prism taller.
"""
import math
from cube.polyhedral import Spec

KINDS={'pentagonal_domino':2,'pentagonal_prism':3,
       'pentagonal_4':4,'professor_pentagonal':5}


def specification(kind,n):
    if KINDS.get(kind)!=n:raise ValueError('Unsupported pentagonal prism order')
    sides=tuple((math.sin(i*2*math.pi/5),0.,math.cos(i*2*math.pi/5)) for i in range(5))
    caps=((0.,1.,0.),(0.,-1.,0.))
    normals=caps+sides
    # Leave a pentagonal centre and ten surrounding patches on each cap.
    # This is the shallow prism,
    # not the deep Pentastar whose cut joins almost-opposite vertices.
    # At a rectangular side, adjacent-axis cuts intersect at +/- one third
    # of its half-width: three equal columns. Professor's intersections are
    # at +/- one fifth and +/- three fifths: five equal columns.
    c=math.cos(2*math.pi/5)
    half_width=math.tan(math.pi/5)
    span=math.sin(2*math.pi/5)*half_width
    depth=c+span/3
    # Positive cap axes carry all horizontal slices, including the bottom.
    # Reference circumradius R -> side inradius R*cos(36 degrees).
    # The 2/3/4-layer prisms keep one common layer thickness; Professor's
    # five thin layers occupy the same total height as the three-layer one.
    height=math.tan(math.pi/5)*(n/3 if n<5 else 1.)
    levels=tuple(height*(1-2*i/n) for i in range(1,n))
    side_cuts=(c+span/5,c+3*span/5) if n==5 else (depth,)
    cuts=(levels,levels)+(side_cuts,)*5
    return Spec(kind,n,normals,normals,(),10,
                axis_steps=(2,2,5,5,5,5,5),axis_cuts=cuts,
                bounds=(height,height)+(1.,)*5)
