"""Five-axis triangular prisms: independent triangle and rectangle turns."""
import math

from cube.polyhedral import Spec


SIDES = tuple((math.sin(i*2*math.pi/3), -math.cos(i*2*math.pi/3), 0.)
              for i in range(3))
NORMALS = SIDES + ((0., 0., 1.), (0., 0., -1.))


def triangular_face_cuts(n):
    """The common triangular layout for prism and Drum caps (2/3, 4/5)."""
    if n not in (2, 3, 4, 5):
        raise ValueError('Unsupported puzzle order')
    k = n//2
    return tuple(1-2*(k-i)/(3*k) for i in range(k))


def prism_specification(n):
    if n not in (2, 3, 4, 5):
        raise ValueError('Unsupported puzzle order')
    # Even prisms retain the radial subdivision of the following odd prism;
    # only the extrusion has an even number of slices (see the product photo).
    radial = triangular_face_cuts(n)
    axial = tuple(-1+2*i/n for i in range(1, n))
    return Spec('pentahedron', n, NORMALS, NORMALS, (), 6,
                axis_steps=(3, 3, 3, 2, 2),
                axis_cuts=(radial,)*3+(axial,)*2)
