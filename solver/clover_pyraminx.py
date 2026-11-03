"""Development-only observed-state solver; the physical shell is unverified."""
from pathlib import Path
from cube.clover_pyraminx import CloverPyraminxCube
from cube.clover_pyraminx_aligned import AlignedCloverPyraminx,generators,source_key,expand,observed_colors
from solver.rigid_colours import MaterialSolver

_profile=MaterialSolver(CloverPyraminxCube,AlignedCloverPyraminx,generators,source_key,expand,observed_colors,'clover_pyraminx_colour_group.bin',complete_group=False)
# This profile deliberately has no directory card and must not add unused
# solver tables to release packages while its photo comparison is failing.
_profile.asset=Path(__file__).resolve().parents[1]/'artifacts/research/clover-pyraminx/colour_group.bin'
ASSET=_profile.asset
prepared=_profile.prepared
validate=_profile.validate
solve_colours=_profile.solve_colours
solve=_profile.solve
