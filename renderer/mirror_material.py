"""Shared silver panels and dark housing for every mirror puzzle renderer."""
from functools import lru_cache

from cube.polyhedral import add, scale, cross, dot, unit, mean, clip

SILVER = (.83, .84, .85, 1.)
HOUSING = (.075, .085, .10, 1.)
UNRECORDED = (.38, .45, .52, 1.)
PANEL_BORDER = .028
LIGHT = unit((-.3, .8, .52))


@lru_cache(maxsize=2048)
def inset_panel(vertices, normal, border=PANEL_BORDER):
    """Inset by physical distance, capped for narrow pieces; accept either winding."""
    centre = mean(vertices)
    edges = []
    for a, b in zip(vertices, vertices[1:]+vertices[:1]):
        delta = add(b, scale(a, -1))
        if dot(delta, delta) < 1e-16:
            continue
        inward = unit(cross(normal, delta))
        if dot(inward, add(centre, scale(a, -1))) < 0:
            inward = scale(inward, -1)
        edges.append((inward, dot(inward, a)))
    if len(edges) < 3:
        return ()
    width = min(border, .18*min(dot(n, centre)-bound for n, bound in edges))
    panel = vertices
    for inward, bound in edges:
        panel = clip(panel, scale(inward, -1), -bound-width)
        if not panel:
            return ()
    return tuple(add(p, scale(normal, .001)) for p in panel)


def shade_surface(normal, eye, silver=True, recorded=True):
    diffuse = max(0., dot(normal, LIGHT))
    if not silver:
        return tuple(v*(.82+.18*diffuse) for v in HOUSING[:3])+(1.,)
    if not recorded:
        return tuple(v*(.82+.18*diffuse) for v in UNRECORDED[:3])+(1.,)
    halfway = add(LIGHT, eye)
    highlight = (max(0., dot(normal, unit(halfway)))**28
                 if dot(halfway, halfway) > 1e-12 else 0.)
    return tuple(min(.98, v*(.76+.24*diffuse)+.16*highlight) for v in SILVER[:3])+(1.,)


def panel_geometry(geometry):
    """Keep the complete housing and overlay an inset silver exterior panel."""
    for points, normal, color, finish, outline in geometry:
        yield points, normal, color, 'cut', outline
        if finish != 'sticker':
            continue
        panel = inset_panel(tuple(points), tuple(normal))
        if panel:
            yield panel, normal, color, 'sticker', tuple((i, (i+1) % len(panel)) for i in range(len(panel)))
