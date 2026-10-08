"""Curved tetrahedral display body, cut into the existing 26 mechanism pieces.

The four colored patches lie on one smooth convex surface. Curve the complete
body first and then cut it with the mechanism's planes, keeping those internal
cuts flat and the small triangular pieces large. Solver geometry is unchanged.
"""

from collections import Counter
from functools import lru_cache
import math

from cube.mastermorphix import NORMALS, VERTICES, _clip, cross, dot
from renderer.polygon_visibility import plane

STYLE_VERSION = "curved_v1"
_SUBDIVISIONS = 14
_CURVATURE = 2.8
_FACE_HEIGHT = 2. / math.sqrt(3.)
_NORMALS = tuple(tuple(v / math.sqrt(3.) for v in n) for n in NORMALS)
_SEAM = .012
_DISPLAY_SCALE = 1.4


@lru_cache(maxsize=2048)
def _curved_point(point):
    """Project radially onto a smooth maximum of the four face planes.

    Unlike an edge bevel, this implicit surface curves across the entire face
    and joins smoothly at the four tips and six colored seams.
    """
    distances = tuple(dot(n, point) for n in _NORMALS)
    low, high = 0., 1.
    for _ in range(28):
        scale = (low + high) / 2.
        level = sum(math.exp(_CURVATURE * (scale*d - _FACE_HEIGHT))
                    for d in distances)
        if level > 1.:
            high = scale
        else:
            low = scale
    scale = (low + high) / 2.
    return tuple(v * scale for v in point)


@lru_cache(maxsize=1)
def _curved_body():
    output = []
    steps = _SUBDIVISIONS
    for color, normal in enumerate(NORMALS):
        corners = [v for v in VERTICES if abs(dot(normal, v)-2.) < 1e-9]
        a, b, c = corners
        if dot(cross(tuple(b[i]-a[i] for i in range(3)),
                     tuple(c[i]-a[i] for i in range(3))), normal) < 0:
            b, c = c, b

        def point(i, j):
            return _curved_point(tuple(((steps-i-j)*a[k]+i*b[k]+j*c[k]) / steps
                                       for k in range(3)))

        for i in range(steps):
            for j in range(steps-i):
                output.append(((point(i, j), point(i+1, j), point(i, j+1)), color))
                if i+j < steps-1:
                    output.append(((point(i+1, j), point(i+1, j+1), point(i, j+1)), color))
    return tuple(output)


def _clip_patch(points, normal, bound):
    """Clip a colored patch without creating a cap or facet-sized border."""
    output = []
    for a, b in zip(points, points[1:] + points[:1]):
        da, db = dot(normal, a)-bound, dot(normal, b)-bound
        if da <= 1e-9:
            output.append(a)
        if (da < -1e-9 and db > 1e-9) or (db < -1e-9 and da > 1e-9):
            t = da / (da-db)
            output.append(tuple(a[i]+t*(b[i]-a[i]) for i in range(3)))
    return tuple(output)


@lru_cache(maxsize=26)
def rounded_piece_geometry(home):
    """Return curved exterior facets and flat internal caps for one piece."""
    polygons = _curved_body()
    bounds = []
    for axis, coord in enumerate(home):
        lo, hi = (-2., -.5) if coord == -1 else ((-.5, .5) if coord == 0 else (.5, 2.))
        polygons = _clip(polygons, axis, 1, hi)
        polygons = _clip(polygons, axis, -1, -lo)
        for sign, bound in ((1, hi), (-1, -lo)):
            normal = tuple(float(sign) if i == axis else 0. for i in range(3))
            bounds.append((normal, bound-_SEAM))
    output = []
    for points, color in polygons:
        points = tuple(points)
        if plane(points) is None:
            continue
        if color < 0:
            output.append((points, color, "internal"))
            continue
        output.append((points, color, "shell"))
        sticker = points
        # Trim only real piece boundaries and colored seams, not tessellation.
        seam_bounds = [(tuple(other[i]-_NORMALS[color][i] for i in range(3)), -_SEAM)
                       for index, other in enumerate(_NORMALS) if index != color]
        for normal, bound in bounds + seam_bounds:
            sticker = _clip_patch(sticker, normal, bound)
            if len(sticker) < 3:
                break
        if len(sticker) >= 3 and plane(sticker) is not None:
            # Shell and sticker are coplanar; painter order preserves this
            # insertion order without depth fighting or raised flat tiles.
            output.append((sticker, color, "sticker"))
    # Match the previous model's visible size after rounding the overall body.
    return tuple((tuple(tuple(v*_DISPLAY_SCALE for v in p) for p in points), color, finish)
                 for points, color, finish in output)


def _edge_key(a, b):
    return tuple(sorted((tuple(round(v, 7) for v in a), tuple(round(v, 7) for v in b))))


@lru_cache(maxsize=26)
def piece_outline_indices(home):
    """Suppress tessellation diagonals when outlining a selected piece."""
    geometry = rounded_piece_geometry(home)
    counts = Counter((finish, color, _edge_key(a, b))
                     for points, color, finish in geometry
                     for a, b in zip(points, points[1:] + points[:1]))
    return tuple(tuple((i, (i+1) % len(points)) for i in range(len(points))
                       if counts[finish, color, _edge_key(points[i], points[(i+1) % len(points)])] == 1)
                 for points, color, finish in geometry)
