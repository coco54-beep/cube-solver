"""YJ Yeet Ball: spherical shell on the four-axis Ivy mechanism.

Logical sticker IDs and rigid piece actions are transported without relabelling
from Ivy. The renderer projects their shared boundaries onto a round shell.
"""
from dataclasses import replace
from functools import lru_cache


@lru_cache(maxsize=1)
def geometry():
    from cube.polyhedral import Geometry,geometry as source_geometry
    source=source_geometry('ivy',3)
    return Geometry(replace(source.spec,kind='yeet_ball'),source.stickers,
                    source.pieces,source.centres,source.permutations,source.layers)


def solve(cube,cancel=None,progress=None):
    from cube.polyhedral import PolyhedralPuzzle
    from solver.ivy import solve_ivy
    # Manual colours, not a scramble witness. Both mechanisms have the same
    # panel actions; every returned move is replayed on the actual sphere too.
    work=PolyhedralPuzzle('ivy',3,list(cube.colors))
    word=solve_ivy(work,cancel,progress)
    replay=cube.entered()
    for move in word:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('Yeet Ball replay failed')
    return word
