"""Rigid silver Pyraminx surfaces with the ordinary tetrahedral move axes."""
from cube.mirror_pyraminx import SHELL_OFFSET
from cube.polyhedral import scale
from renderer.mirror_tower_view import MirrorTowerView
from renderer.polyhedral_view import PolyhedralTwistView


class MirrorPyraminxView(MirrorTowerView):
    camera_target = scale(SHELL_OFFSET, .64)


class MirrorPyraminxTwistView(MirrorPyraminxView, PolyhedralTwistView):
    pass
