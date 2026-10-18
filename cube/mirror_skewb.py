"""Mirror Skewb: eight unequal corners and six oriented silver centres."""
from cube.mirror_pyraminx import MirrorPyraminxCube, SHELL_OFFSETS

SHELL_OFFSET = SHELL_OFFSETS['skewb']


class MirrorSkewbCube(MirrorPyraminxCube):
    puzzle_kind = 'mirror_skewb'
    mechanism_kind = 'skewb'
    supported_orders = (3,)
    color_count = 6
