"""Circle 2 input consists of visible colours, with no retained scramble."""
import pytest
from cube.circle_cube import Circle2Cube
from cube.polyhedral_scramble import scramble
from solver.circle_cube import solve_circle


@pytest.mark.parametrize('seed',range(20))
@pytest.mark.parametrize('length',(24,100))
def test_visible_manual_state_solves(seed,length):
    source=Circle2Cube();scramble(source,length,seed)
    entered=Circle2Cube(colors=list(source.colors)).entered()
    assert not entered.circle_history
    before=list(entered.colors);anchor=entered.anchor
    word=solve_circle(entered)
    assert entered.colors==before and entered.anchor==anchor and not entered.circle_history
    replay=entered.clone()
    for move in word:replay.apply_move(move)
    assert replay.is_solved()


def test_cancel_preserves_input():
    source=Circle2Cube();scramble(source,40,7)
    entered=Circle2Cube(colors=source.colors).entered();before=list(entered.colors)
    with pytest.raises(InterruptedError):solve_circle(entered,lambda:True)
    assert entered.colors==before
