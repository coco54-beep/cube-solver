"""Flower dodecahedron with circular edge cuts and hidden corners.

The regular, shape-preserving moves are half turns around thirty edge axes.
Jumbling (partial turns followed by a different axis) is not represented.
"""
import math
from functools import lru_cache

from cube.polyhedral import DODECA, Spec, add, body, cross, dot, key, mean, scale, unit


@lru_cache(maxsize=1)
def edge_caps():
    edges = {}
    for polygon in body(DODECA):
        for a, b in zip(polygon, polygon[1:] + polygon[:1]):
            centre = mean((a, b))
            delta = add(a, scale(b, -1))
            edges[key(centre)] = (centre, math.sqrt(dot(delta, delta)) / 2)
    return tuple(edges.values())


def blossom_specification():
    return Spec('blossom', 3, DODECA,
                tuple(unit(centre) for centre, _ in edge_caps()), (), 2)


def blossom_skin(spec):
    """Five lenses, five edge caps and one concave centre per pentagon.

    Adjacent circles meet at the outer vertex and its reflection across
    their midpoint. Every neighbouring patch shares the same sampled arc.
    """
    fragments = []
    for face, vertices in enumerate(body(spec.normals)):
        normal = spec.normals[face]
        edges = tuple(mean((a, b)) for a, b in
                      zip(vertices, vertices[1:] + vertices[:1]))
        inner = tuple(add(add(edges[i-1], edges[i]), scale(v, -1))
                      for i, v in enumerate(vertices))

        def arc(centre, a, b):
            u, v = add(a, scale(centre, -1)), add(b, scale(centre, -1))
            angle = math.atan2(dot(cross(u, v), normal), dot(u, v))
            tangent = cross(normal, u)
            points = tuple(add(centre, add(scale(u, math.cos(t)),
                                           scale(tangent, math.sin(t))))
                           for t in (angle*j/16 for j in range(17)))
            return (a,) + points[1:-1] + (b,)

        left = tuple(arc(edges[i-1], v, inner[i]) for i, v in enumerate(vertices))
        right = tuple(arc(edges[i], v, inner[i]) for i, v in enumerate(vertices))
        middle = tuple(arc(edges[i], inner[i], inner[(i+1) % 5]) for i in range(5))
        for i, vertex in enumerate(vertices):
            leaf = left[i] + tuple(reversed(right[i][:-1]))
            fragments.append((('leaf', face, key(vertex)), face, leaf))
            cap = left[i] + middle[i][1:] + tuple(reversed(right[(i+1) % 5][:-1]))
            fragments.append((('edge', key(edges[i])), face, cap))
        centre = tuple(p for segment in reversed(middle) for p in reversed(segment[1:]))
        fragments.append((('centre', face), face, centre))
    return fragments
