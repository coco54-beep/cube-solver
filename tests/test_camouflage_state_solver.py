"""Visible six-view entry followed by history-free solve and physical replay."""
import pytest
from cube.cuboid import CuboidCube
from cube.polyhedral_scramble import scramble
from tests.test_camouflage_six_view_entry import enter_visible_panels,visible_state
from solver.cuboid import solve_cuboid


@pytest.mark.parametrize('seed,length',[(20261023,24)]+[(i,40) for i in range(6)]+[(i,100) for i in range(12)])
def test_reentered_camouflage_scrambles_solve(seed,length):
    source=CuboidCube.solved('camouflage_3');scramble(source,length,seed)
    draft=enter_visible_panels(source);result=draft.match(seconds=10)
    assert result.status=='ok'
    cube=result.cube
    assert cube.history is None
    assert visible_state(cube,draft.model)==visible_state(source,draft.model)
    before=visible_state(cube,draft.model);word=solve_cuboid(cube)
    assert cube.history is None and visible_state(cube,draft.model)==before
    for move in word:cube.apply_move(move)
    assert cube.is_solved()


def test_portfolio_shares_one_deadline(monkeypatch):
    import solver.cuboid_search as module
    from types import SimpleNamespace
    clock=[100.];budgets=[]
    monkeypatch.setattr(module,'monotonic',lambda:clock[0])
    def search(cube,cancel,progress,seconds,**kwargs):
        budgets.append(seconds);clock[0]+=seconds
        raise TimeoutError('cuboid.search_budget')
    monkeypatch.setattr(module,'_search_bandaged_cuboid',search)
    with pytest.raises(TimeoutError):module.solve_bandaged_cuboid(SimpleNamespace(puzzle_kind='camouflage_3'),seconds=20.)
    assert sum(budgets)==20. and budgets==[4.,4.,4.,5.,3.]


def test_portfolio_honours_cancellation_between_attempts(monkeypatch):
    import solver.cuboid_search as module
    from types import SimpleNamespace
    attempts=[]
    def search(*args,**kwargs):
        attempts.append(True);raise TimeoutError('cuboid.search_budget')
    monkeypatch.setattr(module,'_search_bandaged_cuboid',search)
    with pytest.raises(InterruptedError):
        module.solve_bandaged_cuboid(SimpleNamespace(puzzle_kind='camouflage_3'),cancel=lambda:bool(attempts))
    assert len(attempts)==1


def test_default_portfolio_continues_instead_of_failing_at_a_time_limit(monkeypatch):
    import solver.cuboid_search as module
    from types import SimpleNamespace
    clock=[100.];budgets=[]
    monkeypatch.setattr(module,'monotonic',lambda:clock[0])
    def search(cube,cancel,progress,seconds,**kwargs):
        budgets.append(seconds)
        if seconds is None:return ('verified-example',)
        clock[0]+=seconds;raise TimeoutError('cuboid.search_budget')
    monkeypatch.setattr(module,'_search_bandaged_cuboid',search)
    assert module.solve_bandaged_cuboid(SimpleNamespace(puzzle_kind='camouflage_3'))==('verified-example',)
    assert budgets==[4.,4.,4.,5.,5.,7.,5.,None]


def test_actual_complete_search_runs_after_fast_attempts_are_exhausted(monkeypatch):
    import solver.cuboid_search as module
    original_search=module._search_bandaged_cuboid
    def limited_fast(cube,cancel,progress,seconds,**kwargs):
        if seconds is not None:raise TimeoutError('cuboid.search_budget')
        return original_search(cube,cancel,progress,None)
    monkeypatch.setattr(module,'_search_bandaged_cuboid',limited_fast)
    source=CuboidCube.solved('camouflage_3');scramble(source,6,37)
    draft=enter_visible_panels(source);cube=draft.match().cube;before=visible_state(cube,draft.model)
    word=solve_cuboid(cube)
    assert cube.history is None and visible_state(cube,draft.model)==before
    replay=cube.clone();replay.apply_moves(word);assert replay.is_solved()
