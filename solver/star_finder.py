"""History-independent staged solving of closed Star Finder positions.

The offline certificate covers all directed triples in each of the four
piece orbits and all pairs in the thirty-edge flip orbit. No entered state
uses the scramble sequence as a witness.
"""
from solver.rex_dodecahedron import solve as solve_staged, validate


def solve(cube,cancel=None,progress=None):
    if cube.puzzle_kind!='kairis_star_finder' or cube.n!=3:
        raise ValueError('Unsupported Star Finder mechanism')
    return solve_staged(cube,cancel,progress)
