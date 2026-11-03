"""Photo-derived twenty-axis Star Finder, in closed 120-degree positions.

This is a deep-cut truncated icosahedron, not a 32-axis Tuttminx. The three
neighbouring hexagon axes cut a hexagon through its centre; that condition
fixes the depth rather than introducing an arbitrary visual subdivision.
The photographs do not certify partial turns or internal track clearance.
"""
from functools import lru_cache
from cube.football import shell_planes
from cube.polyhedral import Spec, dot


@lru_cache(maxsize=1)
def specification():
    planes = shell_planes()
    normals = tuple(n for n, bound, colour in planes)
    bounds = tuple(bound for n, bound, colour in planes)
    axes = normals[12:]
    adjacent = max(dot(axes[0], n) for n in axes if dot(axes[0], n) < 1-1e-8)
    depth = bounds[12] * adjacent
    return Spec('kairis_star_finder', 3, normals, axes, (depth,), 3, bounds=bounds)
