"""Observed-state solving on the independent suncube material profile."""
from cube.suncube import SunCube
from cube.suncube_aligned import AlignedSunCube,generators,source_key,expand,observed_colors
from solver.rigid_colours import MaterialSolver

_profile=MaterialSolver(SunCube,AlignedSunCube,generators,source_key,expand,observed_colors,'suncube_colour_group.bin')
ASSET=_profile.asset
prepared=_profile.prepared
local_patterns=_profile.local_patterns
validate=_profile.validate
solve_colours=_profile.solve_colours
solve=_profile.solve
