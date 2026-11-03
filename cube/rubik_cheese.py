"""Anthony Greenhill's two-layer Rubik Cheese, as specified by the user.

This entry deliberately does not model the earlier single-layer Cheese.
"""
from cube.layered_cheese import cheese_geometry as _geometry,skin


def cheese_geometry():return _geometry('rubik_cheese')
def goal_colors():return tuple(s.face for s in cheese_geometry().stickers)
