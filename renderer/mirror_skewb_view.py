"""Rigid unequal Skewb shell in silver, including exposed cut surfaces."""
from cube.mirror_skewb import SHELL_OFFSET
from cube.polyhedral import scale
from renderer.mirror_tower_view import MirrorTowerView
from renderer.polyhedral_view import PolyhedralTwistView


class MirrorSkewbView(MirrorTowerView):
    camera_target = scale(SHELL_OFFSET, .64)


class MirrorSkewbTwistView(MirrorSkewbView, PolyhedralTwistView):
    pass
