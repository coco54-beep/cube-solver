"""History-independent observed-state solving on guarded Pisces material."""
from cube.pisces import PiscesCube
from cube.pisces_aligned import AlignedPisces,generators,source_key,expand,observed_colors
from solver.rigid_colours import MaterialSolver

_profile=MaterialSolver(PiscesCube,AlignedPisces,generators,source_key,expand,observed_colors,'pisces_colour_group.bin',complete_group=False)
ASSET=_profile.asset
prepared=_profile.prepared
validate=_profile.validate
solve_colours=_profile.solve_colours
solve=_profile.solve
