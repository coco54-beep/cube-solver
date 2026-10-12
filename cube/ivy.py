"""Four-axis Ivy Cube: four rotating corners and six leaf centres."""
import math
from cube.polyhedral import CUBE, TETRA, Spec, add, body, cross, dot, key, scale


def ivy_specification():
    return Spec('ivy', 3, CUBE, tuple(scale(n, -1) for n in TETRA), (0.,), 3)


def ivy_skin(spec):
    """Opposite quarter circles tile every face with exactly three panels.

    Each circle is centred on an active corner and has one face-edge length
    as its radius. The opposite corner panel is outside this circle; their
    intersection forms the leaf. Whole corner panels move as rigid pieces.
    """
    active = {key(scale(axis, math.sqrt(3))) for axis in spec.axes}
    fragments = []
    for face, vertices in enumerate(body(CUBE)):
        first = next(i for i, p in enumerate(vertices) if key(p) in active)
        a, b, c, d = tuple(vertices[(first+i) % 4] for i in range(4))
        normal = spec.normals[face]

        def arc(centre, start, end):
            u, v = add(start, scale(centre, -1)), add(end, scale(centre, -1))
            angle = math.atan2(dot(cross(u, v), normal), dot(u, v))
            tangent = cross(normal, u)
            return (start,) + tuple(add(centre, add(scale(u, math.cos(t)),
                                                    scale(tangent, math.sin(t))))
                                   for t in (angle*i/24 for i in range(1, 24))) + (end,)

        near_a = arc(c, b, d)
        near_c = arc(a, d, b)
        fragments.append((('corner', key(a)), face, (a,) + near_a))
        fragments.append((('corner', key(c)), face, (c,) + near_c))
        leaf = near_a + near_c[1:-1]
        fragments.append((('leaf', face), face, leaf))
    return fragments
