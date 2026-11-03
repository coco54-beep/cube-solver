"""Observed-state solving for the independently constructed Curvy Hexagram."""
from cube.hexagram import HexagramCube
from cube.hexagram_aligned import AlignedHexagram,generators,source_key,expand,observed_colors
from solver.rigid_colours import MaterialSolver

_profile=MaterialSolver(HexagramCube,AlignedHexagram,generators,source_key,expand,observed_colors,'hexagram_colour_group.bin',complete_group=False)
ASSET=_profile.asset
prepared=_profile.prepared
validate=_profile.validate
solve_colours=_profile.solve_colours
solve=_profile.solve
