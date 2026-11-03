"""Native edge/pentagon quotient followed by a pure petal cycle."""
import pytest
from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble
from solver.starminx import solve_starminx,asset


@pytest.mark.parametrize('length',(30,100,300))
@pytest.mark.parametrize('seed',range(8))
def test_history_free_deep_states_preserve_input_and_replay_all_stages(seed,length):
    source=PolyhedralPuzzle('starminx_i',3);scramble(source,length,seed)
    cube=PolyhedralPuzzle('starminx_i',3,list(source.colors));before=list(cube.colors)
    word=solve_starminx(cube)
    assert cube.colors==before and not cube.scramble_history
    assert len(word)<2500
    for move in word:cube.apply_move(move)
    assert cube.is_solved()


def test_stage_guard_and_cancellation_preserve_the_entered_state(monkeypatch):
    import solver.starminx as module
    cube=PolyhedralPuzzle('starminx_i',3);scramble(cube,100,900)
    before=list(cube.colors);calls=0
    def cancel():
        nonlocal calls
        calls+=1;return calls>35
    with pytest.raises(InterruptedError):solve_starminx(cube,cancel)
    assert cube.colors==before
    bad=dict(asset(),geometry='wrong')
    monkeypatch.setattr(module,'asset',lambda:bad)
    with pytest.raises(ValueError,match='does not match'):solve_starminx(cube)
    assert cube.colors==before
