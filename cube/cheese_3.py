"""Three-layer Cheese, with the solid face scheme in the user's reference."""
from cube.layered_cheese import cheese_geometry as _geometry,skin


def cheese_geometry():return _geometry('cheese_3')
def goal_colors():return tuple(s.face for s in cheese_geometry().stickers)
def curved_skin():return skin('cheese_3')
