"""Replay-verified and observed-state solving for the Curvy Hexagram."""
from time import monotonic

from cube.hexagram import HexagramCube
from cube.hexagram_aligned import AlignedHexagram,generators,source_key,expand,observed_colors
from solver.rigid_colours import MaterialSolver
from solver.rigid_shape import solve_recorded_turns

_profile=MaterialSolver(HexagramCube,AlignedHexagram,generators,source_key,expand,observed_colors,'hexagram_colour_group.bin',complete_group=False)
ASSET=_profile.asset
prepared=_profile.prepared
validate=_profile.validate
solve_colours=_profile.solve_colours


def solve(cube, cancel=None, progress=None, seconds=60.):
    deadline = monotonic() + seconds

    def guard():
        if cancel and cancel():
            raise InterruptedError()
        if monotonic() >= deadline:
            raise TimeoutError('comet.timeout')

    guard()
    recorded = solve_recorded_turns(cube, guard)
    if recorded is not None:
        return recorded
    return _profile.solve(cube, cancel, progress, max(0., deadline - monotonic()))
