"""Order convex surfaces without hiding nearer faces behind large tilted faces.

A surface's average depth is insufficient for a shape-changing puzzle. Split
surfaces at intervening planes and traverse the resulting BSP from far to near.
Keep only original boundary segments, so the splits do not add visible seams.
"""

from dataclasses import dataclass
from math import sqrt

from cube.mastermorphix import cross, dot


_EPSILON = 1e-7


@dataclass
class Surface:
    vertices: tuple
    edges: tuple
    payload: tuple

    @classmethod
    def polygon(cls, vertices, payload):
        vertices = tuple(vertices)
        return cls(vertices, tuple(zip(vertices, vertices[1:] + vertices[:1])), payload)


def plane(vertices):
    """Return a unit outward normal, also allowing collinear clipping vertices."""
    a = vertices[0]
    for b, c in zip(vertices[1:], vertices[2:]):
        normal = cross(tuple(b[i]-a[i] for i in range(3)),
                       tuple(c[i]-a[i] for i in range(3)))
        length = sqrt(dot(normal, normal))
        if length > _EPSILON:
            normal = tuple(value/length for value in normal)
            return normal, dot(normal, a)
    return None


def _clip(surface, normal, bound, sign):
    def distance(point):
        return sign * (dot(normal, point)-bound)

    def intersection(a, b, da, db):
        t = da/(da-db)
        return tuple(a[i]+t*(b[i]-a[i]) for i in range(3))

    vertices = []
    for a, b in zip(surface.vertices, surface.vertices[1:] + surface.vertices[:1]):
        da, db = distance(a), distance(b)
        if da >= -_EPSILON:
            vertices.append(a)
        if (da < -_EPSILON and db > _EPSILON) or (da > _EPSILON and db < -_EPSILON):
            vertices.append(intersection(a, b, da, db))
    if len(vertices) < 3 or plane(vertices) is None:
        return None
    edges = []
    for a, b in surface.edges:
        da, db = distance(a), distance(b)
        if da < -_EPSILON and db < -_EPSILON:
            continue
        if da < -_EPSILON:
            a = intersection(a, b, da, db)
        elif db < -_EPSILON:
            b = intersection(a, b, da, db)
        if sum((a[i]-b[i])**2 for i in range(3)) > _EPSILON**2:
            edges.append((a, b))
    return Surface(tuple(vertices), tuple(edges), surface.payload)


def painter_order(surfaces, forward):
    """Yield surface fragments in correct orthographic painter order."""
    if not surfaces:
        return
    # Median input keeps the tree shallow for the regular cubie enumeration.
    splitter = surfaces[len(surfaces)//2]
    normal, bound = plane(splitter.vertices)
    positive, negative, coplanar = [], [], []
    for surface in surfaces:
        distances = [dot(normal, p)-bound for p in surface.vertices]
        lo, hi = min(distances), max(distances)
        if lo >= -_EPSILON and hi <= _EPSILON:
            coplanar.append(surface)
        elif lo >= -_EPSILON:
            positive.append(surface)
        elif hi <= _EPSILON:
            negative.append(surface)
        else:
            for sign, branch in ((1, positive), (-1, negative)):
                fragment = _clip(surface, normal, bound, sign)
                if fragment is not None:
                    branch.append(fragment)
    far, near = (negative, positive) if dot(normal, forward) < 0 else (positive, negative)
    yield from painter_order(far, forward)
    yield from coplanar
    yield from painter_order(near, forward)
