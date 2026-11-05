"""YJ Yeet Ball: spherical shell on the four-axis Ivy mechanism.

Logical sticker IDs and rigid piece actions are transported without relabelling
from Ivy. Mechanical seams are plane/sphere circles, not projected Ivy arcs.
"""
from dataclasses import replace
from functools import lru_cache
import math

RADIUS=math.sqrt(3)
# pCubes Yeet Ball: D=C15/sqrt(3), where sqrt(3)*C15 is the
# radius at a body diagonal. Thus the smooth sphere has D/R=1/3.
# This makes adjacent caps meet at the four opposite-axis tips.
CUT_HEIGHT=RADIUS/3
CUT_RADIUS=math.sqrt(RADIUS**2-CUT_HEIGHT**2)


@lru_cache(maxsize=1)
def geometry():
    from cube.polyhedral import Geometry,Sticker,geometry as source_geometry,unit,add,scale
    from cube.spherical_surfaces import outline
    source=source_geometry('ivy',3)
    stickers=[]
    for sticker in source.stickers:
        face=source.spec.normals[sticker.face]
        # Preserve the existing six colour regions and physical piece IDs.
        # A leaf belongs to two caps; a three-colour corner belongs to one.
        planes=tuple((unit(add(n,scale(face,-1))),0.)
                     for n in source.spec.normals if n!=face)
        for axis,bands in zip(source.spec.axes,source.layers):
            inside=sticker.piece in bands[0]
            planes+=((scale(axis,-1) if inside else axis,
                      -CUT_HEIGHT if inside else CUT_HEIGHT),)
        stickers.append(Sticker(sticker.piece,sticker.face,outline(planes,RADIUS,segments=96)))
    return Geometry(replace(source.spec,kind='yeet_ball'),tuple(stickers),
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
