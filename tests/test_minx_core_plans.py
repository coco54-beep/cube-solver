"""Bundled plans protect the solved core and every earlier centre orbit."""
import pytest

from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import apply_word,piece_orbits
from solver.minx_plans import core_orbit_plan


def parts(cube):
    g=cube.geometry
    orbits=piece_orbits(cube.puzzle_kind,cube.n)
    core={i for i,o in enumerate(orbits) if len(g.pieces[o[0]])==3 or
          (len(o)==30 and len(g.pieces[o[0]])==2)}
    targets={i:o for i,o in enumerate(orbits) if len(o)>1 and i not in core}
    guarded={s for i in core for p in orbits[i] for s in g.pieces[p]}
    return targets,guarded


@pytest.mark.parametrize('n',range(4,14))
def test_prepared_macros_protect_core_and_solved_orbits(n):
    cube=PolyhedralPuzzle.solved('megaminx',n)
    g=cube.geometry
    targets,guarded=parts(cube)
    plan=core_orbit_plan(cube,targets)
    assert plan is not None
    macros,order,staged=plan
    for index in order:
        word,base=macros[index]
        permutation=apply_word(g,word)
        moving={s for p in targets[index] for s in g.pieces[p]}
        fixed=guarded if staged else set(range(len(g.stickers)))-moving
        assert all(permutation[s]==s for s in fixed)
        assert {p for p in targets[index] if g.stickers[permutation[g.pieces[p][0]]].piece!=p}==set(base)
        guarded.update(moving)


def test_legacy_pipeline_does_not_search_macros_when_prepared(monkeypatch):
    from solver import polyhedral_reduction as reduction
    cube=PolyhedralPuzzle.solved('megaminx',13)
    cube.apply_move(cube.moves()[0])
    def unexpected(*args,**kwargs): raise AssertionError('Prepared macros were ignored')
    monkeypatch.setattr(reduction,'primitives',unexpected)
    solution=reduction._solve_high_minx_legacy(cube)
    for move in solution: cube.apply_move(move)
    assert cube.is_solved()
