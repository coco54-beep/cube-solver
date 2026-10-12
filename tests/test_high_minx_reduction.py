"""高阶五魔方原生环降阶（solver/high_minx_reduction.py）回归。

验证 beam + 三循环清理 + 角块扭转修正的流水线能正确还原，且角块扭转 gadget
确实是只扭转角块、不动其它块、也不改角块位置的纯扭转。
"""

import pytest

from cube.polyhedral import PolyhedralPuzzle, Move
from solver.polyhedral import (apply_word, compose, piece_orbits, scramble,
                               solve_polyhedral)
from solver import high_minx_reduction as R


def _solved(cube, solution):
    work = cube.entered()
    for move in solution:
        work.apply_move(move)
    return work.is_solved()


@pytest.mark.parametrize("n,seed", [(4, 3), (6, 3)])
def test_reduced_pipeline_solves(n, seed):
    cube = PolyhedralPuzzle("megaminx", n)
    scramble(cube, 12, seed=seed)
    solution = solve_polyhedral(cube)
    assert _solved(cube, solution)
    # The reduction is only worth using when it beats the legacy solve.
    assert len(solution) < 900 if n == 4 else len(solution) < 1200


@pytest.mark.parametrize("n", [4, 6])
def test_twist_gadget_is_pure(n):
    cube = PolyhedralPuzzle("megaminx", n)
    g = cube.geometry
    corners = next(o for o in piece_orbits("megaminx", n)
                   if len(g.pieces[o[0]]) == 3)
    corner_stickers = {s for p in corners for s in g.pieces[p]}
    gadget = R.build_twist_gadget(cube, corners)
    assert gadget is not None
    word, base, vec = gadget
    perm = apply_word(g, word)
    # Nothing outside the corners moves.
    assert all(perm[s] == s for s in range(len(g.stickers))
               if s not in corner_stickers)
    # Every corner keeps its position; exactly three are twisted.
    twisted = 0
    for p in corners:
        assert {perm[s] for s in g.pieces[p]} == set(g.pieces[p])
        if tuple(perm[s] for s in g.pieces[p]) != tuple(g.pieces[p]):
            twisted += 1
    assert twisted == 3
