"""Retry retains a frontier, not a solution history or a cancelled closure."""
from collections import Counter
from itertools import count
import pytest
from solver.complete_search import deepen
from solver import search_resume as store


@pytest.fixture(autouse=True)
def clean():
    store.clear();yield;store.clear()


@pytest.mark.parametrize('stop_at',(3,12,25,28))
def test_cancel_retry_uses_new_callbacks_and_does_not_repeat_expanded_nodes(stop_at):
    calls=Counter();guards=count()
    def children(s):calls[s]+=1;return ((s+1,s+1),) if s<30 else ()
    args=(0,lambda s:() if s==30 else None,children,lambda s:30-s)
    with pytest.raises(InterruptedError):
        deepen(*args,cancel=lambda:next(guards)>=stop_at,resume_key='chain')
    before=sum(calls.values());assert store._entries
    events=[]
    with store.reporting(events.append):word=deepen(*args,cancel=lambda:False,resume_key='chain')
    assert word==tuple(range(1,31)) and not store._entries
    assert max(calls.values())==1 and sum(calls.values())>=before
    assert any(e['search']['resumed'] for e in events)


def test_cancel_inside_child_generation_does_not_commit_a_partial_expansion():
    broken=[True]
    def children(s):
        yield s+1,s+1
        if broken[0]:raise InterruptedError()
    with pytest.raises(InterruptedError):
        deepen(0,lambda s:() if s==4 else None,children,lambda s:4-s,resume_key='generator')
    broken[0]=False
    assert deepen(0,lambda s:() if s==4 else None,children,lambda s:4-s,resume_key='generator')==(1,2,3,4)


def test_deadline_is_resumable_and_changed_input_is_not_reused(monkeypatch):
    import solver.complete_search as module
    clock=count(0,.1);monkeypatch.setattr(module,'monotonic',lambda:next(clock))
    args=(0,lambda s:() if s==20 else None,lambda s:((s+1,s+1),),lambda s:20-s)
    with pytest.raises(TimeoutError):deepen(*args,resume_key='deadline',seconds=.9)
    assert len(store._entries)==1
    with pytest.raises(TimeoutError):deepen(5,*args[1:],resume_key='deadline',seconds=.5)
    assert len(store._entries)==2
    assert deepen(*args,resume_key='deadline')==tuple(range(1,21))


def test_checkpoint_storage_is_bounded_and_simultaneous_workers_do_not_share():
    for i in range(4):
        with store.checkpoint('bounded',i) as item:
            item.expanded=i
            with pytest.raises(InterruptedError):
                with store.checkpoint('bounded',i) as other:
                    assert other is not item;raise InterruptedError()
            # Keep the outer checkpoint too.
            with store._lock:assert len(store._entries)<=2
    for i in range(4):
        with pytest.raises(InterruptedError):
            with store.checkpoint('bounded',i):raise InterruptedError()
    assert len(store._entries)==store.MAX_CHECKPOINTS


def test_mixup_retry_skips_failed_fast_phase_and_replays_a_real_solution(monkeypatch):
    import solver.mixup as module
    import solver.mixup_complete as complete
    from cube.mixup import MixupCube
    from cube.polyhedral import Move
    cube=MixupCube('mixup_333');cube.apply_move(Move(1,1,1));cube.history=[]
    failures=[];original=complete.solve_complete
    def limited(*args):failures.append(True);raise ValueError('mixup.shape_limit')
    def pause(*args,**kwargs):raise InterruptedError()
    monkeypatch.setattr(module,'_restore_shape',limited);monkeypatch.setattr(complete,'solve_complete',pause)
    with pytest.raises(InterruptedError):module.solve_mixup(cube)
    monkeypatch.setattr(complete,'solve_complete',original)
    result=module.solve_mixup(cube);work=cube.clone();work.apply_moves(result.moves)
    assert len(failures)==1 and result.success and work.is_solved() and not cube.history


def test_production_mixup_reuses_a_real_cancelled_physical_search_frontier(monkeypatch):
    import solver.mixup as module
    import solver.complete_search as engine
    from cube.mixup import MixupCube
    from cube.polyhedral import Move
    from services.solve_service import SolveService,CancelToken
    from services.solution_cache import clear
    clear();cube=MixupCube('mixup_333');cube.apply_move(Move(1,1,1));cube.history=[]
    fast_calls=[]
    def limited(*args):fast_calls.append(True);raise ValueError('mixup.shape_limit')
    monkeypatch.setattr(module,'_restore_shape',limited)
    clock=count(0.,.25);monkeypatch.setattr(engine,'monotonic',lambda:next(clock))
    token=CancelToken();first=[];updates=[]
    def pause(payload):
        updates.append(payload)
        if payload.get('search',{}).get('expanded',0)>0:token.cancel()
    SolveService()._run(cube.clone(),first.append,pause,token)
    assert first[0].failure_category=='cancelled' and store._entries
    assert any(p.get('search',{}).get('expanded',0)>0 for p in updates)
    second=[];updates=[]
    SolveService()._run(cube.clone(),second.append,updates.append,CancelToken())
    assert second[0].success and len(fast_calls)==1
    assert any(p.get('search',{}).get('resumed') for p in updates)
    replay=cube.clone();replay.apply_moves(second[0].moves)
    assert replay.is_solved() and not cube.history and not store._entries
    clear()


def test_retry_waits_for_the_old_worker_and_can_cancel_while_waiting():
    from threading import Thread,Event
    waiting=Event();cancel=Event();done=[]
    with store.checkpoint('worker',0) as first:
        first.expanded=7
        def retry():
            waiting.set()
            try:
                with store.checkpoint('worker',0,cancel.is_set) as second:done.append(second.expanded)
            except InterruptedError:done.append('cancelled')
        thread=Thread(target=retry);thread.start();assert waiting.wait(1)
        cancel.set();thread.join(1)
        assert done==['cancelled'] and first.expanded==7

