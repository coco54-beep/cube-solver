"""Replay checkpoints preserve material poses as well as visible colours."""
from cube.cuboid import CUBOID_PREFIXES


def full_state(cube):
    return (cube.puzzle_kind.startswith(CUBOID_PREFIXES+('circle_2',))
            or hasattr(cube,'frames') and hasattr(cube,'paints'))


def capture(cube):return cube.clone() if full_state(cube) else tuple(cube.colors)


def restore(cube,snapshot):
    if full_state(cube):cube.restore(snapshot)
    else:cube.colors=list(snapshot)
