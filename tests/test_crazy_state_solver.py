"""Planet inputs use actual inner/outer paint and no remembered inverse."""
import pytest
from cube.circle_cube import KINDS
from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble
from solver.circle_cube import solve_circle
from solver.circle2_group import table


@pytest.mark.parametrize('kind',KINDS)
@pytest.mark.parametrize('seed',range(6))
@pytest.mark.parametrize('length',(24,100))
def test_planet_visible_manual_state_solves(kind,seed,length):
    source=PolyhedralPuzzle(kind,3);scramble(source,length,seed)
    cube=PolyhedralPuzzle(kind,3,list(source.colors)).entered();before=list(cube.colors)
    assert not cube.circle_history
    word=solve_circle(cube)
    assert cube.colors==before and not cube.circle_history
    for move in word:cube.apply_move(move)
    assert cube.is_solved()


@pytest.mark.parametrize('kind',KINDS)
def test_cancel_and_resource_model_guard(monkeypatch,kind):
    import solver.circle2_group as module
    source=PolyhedralPuzzle(kind,3);scramble(source,24,7)
    cube=PolyhedralPuzzle(kind,3,list(source.colors));before=list(cube.colors)
    with pytest.raises(InterruptedError):solve_circle(cube,lambda:True)
    assert cube.colors==before
    table.cache_clear()
    with monkeypatch.context() as patch:
        patch.setattr(module,'fingerprint',lambda kind:'different mechanism')
        with pytest.raises(ValueError,match='circle2.table_version'):table(kind)
    table.cache_clear()
