"""History-independent solving for the pCubes Twins reference mechanism."""
from cube.twins_pcubes import TwinsPCubesState
from cube.twins_pcubes_aligned import AlignedTwinsPCubes,generators,source_key,expand,observed_colors
from solver.rigid_colours import MaterialSolver

_profile=MaterialSolver(TwinsPCubesState,AlignedTwinsPCubes,generators,source_key,expand,observed_colors,
                        'twins_pcubes_colour_group.bin',complete_group=False)
ASSET=_profile.asset
validate=_profile.validate
prepared=_profile.prepared
solve_colours=_profile.solve_colours
solve=_profile.solve
