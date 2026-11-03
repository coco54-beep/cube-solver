"""Shared materials and seams for unfinished and coloured puzzle surfaces.

Colours and lighting are pure Python so geometry builders need no window.
Stroke widths are half-widths, matching both Kivy Line and mesh ribbons.
"""
from math import sqrt

UNENTERED = (.43, .48, .53, 1.)
PLASTIC = (.12, .15, .18, 1.)
SEAM = (.12, .16, .20, 1.)
GRID = (.27, .32, .37, .48)
SELECTION = (.05, .84, 1., 1.)
_LIGHT_LENGTH = sqrt(.3**2+.8**2+.52**2)
LIGHT = tuple(v/_LIGHT_LENGTH for v in (-.3, .8, .52))


def surface_panel(points, normal, lift=.0015):
    """Cover the full physical face; screen-space strokes supply its border."""
    return tuple(tuple(v+n*lift for v,n in zip(point,normal)) for point in points)


def shade_unentered(normal):
    brightness = .85+.15*max(0., sum(a*b for a,b in zip(normal,LIGHT)))
    return tuple(v*brightness for v in UNENTERED[:3])+(1.,)


def stroke(role='seam'):
    from kivy.metrics import dp
    return dp({'grid': .4, 'seam': .75, 'outline': 1., 'selection': 1.6}[role])
