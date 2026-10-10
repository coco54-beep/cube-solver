"""Curved tetrahedral display body, cut into mechanical pieces.

The four colored patches lie on one smooth convex surface. Curve the complete
body first and then cut it with the mechanism's planes, keeping those internal
cuts flat and the small triangular pieces large. Solver geometry is unchanged.
"""

from collections import Counter
from functools import lru_cache
import math

from cube.mastermorphix import (NORMALS, VERTICES, _clip, cross, dot,
                               cut_boundaries, positions_for_order)
from renderer.polygon_visibility import plane

STYLE_VERSION = "smooth_morphix_closed_edges_v4"
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


@lru_cache(maxsize=2)
def _curved_body(subdivisions=_SUBDIVISIONS):
    output = []
    steps = subdivisions
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


def _display_boundaries(n):
    if n <= 3:
        return cut_boundaries(n)
    # The smooth 2/3-order shell is smaller than the spherical high-order
    # shell. Fit its inner mechanism planes while preserving every layer.
    # Scale inner cuts only. The enclosing bounds must cover the complete
    # smooth shell; scaling them too truncates its six rounded edges.
    return (-2.,) + tuple(value*.5 for value in cut_boundaries(n)[1:-1]) + (2.,)


@lru_cache(maxsize=12)
def _display_pieces(n, subdivisions):
    vals=sorted({p[0] for p in positions_for_order(n)})
    bounds=_display_boundaries(n)
    def strip(polygons, axis, index):
        lo,hi=bounds[index:index+2]
        return _clip(_clip(polygons,axis,1,hi),axis,-1,-lo)
    result={}
    body=_curved_body(subdivisions)
    for ix,x in enumerate(vals):
        xs=strip(body,0,ix)
        for iy,y in enumerate(vals):
            ys=strip(xs,1,iy)
            for iz,z in enumerate(vals):
                if any(i in (0,n-1) for i in (ix,iy,iz)):
                    result[x,y,z]=strip(ys,2,iz)
    return result


@lru_cache(maxsize=2048)
def rounded_piece_geometry(home, subdivisions=_SUBDIVISIONS, n=3):
    """Return curved exterior facets and flat internal caps for one piece."""
    # A curved facet is never given its own border. Piece/color boundaries
    # below are the only places where the white backing is exposed.
    polygons = (_curved_body(subdivisions) if n <= 3 else
                _display_pieces(n, max(12, subdivisions))[home])
    bounds = []
    from cube.mastermorphix import positions_for_order
    vals = sorted({p[0] for p in positions_for_order(n)})
    # Cut the curved body with flat mechanism planes, rather than bending a
    # subdivided cube grid. This preserves the real eight-piece 2x2 layout.
    boundaries = _display_boundaries(n)
    for axis, coord in enumerate(home):
        index = vals.index(coord)
        lo, hi = boundaries[index], boundaries[index+1]
        if n <= 3:
            polygons = _clip(polygons, axis, 1, hi)
            polygons = _clip(polygons, axis, -1, -lo)
        for sign, bound in ((1, hi), (-1, -lo)):
            normal = tuple(float(sign) if i == axis else 0. for i in range(3))
            bounds.append((normal, bound-_SEAM))
    output = []
    exterior_colors = sorted({color for _, color in polygons if color >= 0})
    for points, color in polygons:
        points = tuple(points)
        if plane(points) is None:
            continue
        if color < 0:
            # Extend the nearest colored face onto exposed mechanism cuts.
            # Split multi-color caps at equal-distance face boundaries, so a
            # two/three-color piece keeps its adjacent colors when deformed.
            for adjacent_color in exterior_colors:
                patch = points
                for other_color in exterior_colors:
                    if other_color == adjacent_color:
                        continue
                    normal = tuple(_NORMALS[other_color][i] -
                                   _NORMALS[adjacent_color][i] for i in range(3))
                    patch = _clip_patch(patch, normal, 0.)
                    if len(patch) < 3:
                        break
                if len(patch) >= 3 and plane(patch) is not None:
                    output.append((patch, adjacent_color, "internal"))
            continue
        if n > 3:
            # Draw the complete continuous color patch. The renderer traces
            # its real boundary once, instead of offsetting every tiny facet
            # against a coplanar white backing (which produces dotted seams).
            output.append((points, color, "sticker"))
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
    display_scale = _DISPLAY_SCALE
    return tuple((tuple(tuple(v*display_scale for v in p) for p in points), color, finish)
                 for points, color, finish in output)


def _edge_key(a, b):
    return tuple(sorted((tuple(round(v, 7) for v in a), tuple(round(v, 7) for v in b))))


@lru_cache(maxsize=2048)
def piece_outline_indices(home, subdivisions=_SUBDIVISIONS, n=3):
    """Suppress tessellation diagonals when outlining a selected piece."""
    geometry = rounded_piece_geometry(home, subdivisions, n)
    counts = Counter((finish, color, _edge_key(a, b))
                     for points, color, finish in geometry
                     for a, b in zip(points, points[1:] + points[:1]))
    return tuple(tuple((i, (i+1) % len(points)) for i in range(len(points))
                       if counts[finish, color, _edge_key(points[i], points[(i+1) % len(points)])] == 1)
                 for points, color, finish in geometry)


@lru_cache(maxsize=4096)
def oriented_piece_geometry(home, frame, subdivisions=_SUBDIVISIONS, n=3):
    """Reuse discrete orientations with a bounded cache on mobile devices."""
    from cube.mastermorphix import transform
    return tuple((tuple(transform(frame, p) for p in points),
                  transform(frame, plane(points)[0]), color, finish, outline)
                 for (points, color, finish), outline in
                  zip(rounded_piece_geometry(home, subdivisions, n),
                     piece_outline_indices(home, subdivisions, n)))
