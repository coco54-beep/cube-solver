"""Super Ivy (Rex): eight spherical corner turns and 42 moving pieces."""
import math

from cube.polyhedral import CUBE, Spec, add, body, cross, dot, key, mean, scale, unit


def super_ivy_specification():
    vertices = {key(p): p for face in body(CUBE) for p in face}
    return Spec('super_ivy', 3, CUBE,
                tuple(unit(vertices[k]) for k in sorted(vertices)), (), 3)


def super_ivy_skin(spec):
    """Four radius-one quarter circles tile every unit square without holes.

    The nine panels are one centre, four single-colour leaves and four edge
    caps. Only the caps are joined into two-sticker pieces across cube edges.
    """
    fragments = []
    h = 1 - math.sqrt(3) / 2
    joins = ((.5, h), (1-h, .5), (.5, 1-h), (h, .5))
    corners = ((0., 0.), (1., 0.), (1., 1.), (0., 1.))

    def arc(centre, start, end):
        first = math.atan2(start[1]-centre[1], start[0]-centre[0])
        last = math.atan2(end[1]-centre[1], end[0]-centre[0])
        angle = (last-first+math.pi) % (2*math.pi) - math.pi
        return (start,) + tuple((centre[0]+math.cos(first+angle*i/16),
                                centre[1]+math.sin(first+angle*i/16))
                               for i in range(1, 16)) + (end,)

    leaves = []
    inner = []
    for i, corner in enumerate(corners):
        left = arc(corners[(i+3) % 4], corner, joins[i])
        middle = arc(corners[(i+2) % 4], joins[i], joins[i-1])
        right = arc(corners[(i+1) % 4], joins[i-1], corner)
        leaves.append(left + middle[1:] + right[1:-1])
        inner.append(middle)
    centre = tuple(p for segment in inner for p in reversed(segment[1:]))

    for face, vertices in enumerate(body(CUBE)):
        v0, v1, _v2, v3 = vertices
        e1, e2 = add(v1, scale(v0, -1)), add(v3, scale(v0, -1))

        def emit(signature, cell):
            polygon = tuple(add(v0, add(scale(e1, x), scale(e2, y))) for x, y in cell)
            normal = spec.normals[face]
            area = sum(dot(cross(a, b), normal)
                       for a, b in zip(polygon, polygon[1:]+polygon[:1]))
            if area < 0:
                polygon = tuple(reversed(polygon))
            fragments.append((signature, face, polygon))

        emit(('centre', face), centre)
        for i, corner in enumerate(corners):
            emit(('leaf', face, key(vertices[i])), leaves[i])
            nxt = corners[(i+1) % 4]
            first = arc(corners[(i+2) % 4], nxt, joins[i])
            second = arc(corners[(i+3) % 4], joins[i], corner)
            cap = (corner, nxt) + first[1:] + second[1:-1]
            emit(('edge', key(mean((vertices[i], vertices[(i+1) % 4])))), cap)
    return fragments
