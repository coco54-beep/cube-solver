"""The application exposes ongoing physical searches without false progress."""
from types import SimpleNamespace
from cube.pentacle import PentacleCube
from services.solve_service import SolveService


def test_indefinite_physical_search_reports_a_cancellable_status(monkeypatch):
    import solver.articulated as module
    source=PentacleCube();before=source.colors;results=[];updates=[]
    def solver(cube,cancel,progress):
        progress(-1,0)
        return ()
    monkeypatch.setattr(module,'solve_articulated',solver)
    SolveService()._run(source,results.append,updates.append,SimpleNamespace(is_set=lambda:False))
    assert results[0].success and source.colors==before
    assert updates==[{'label':'solver.continuing','progress':0.}]


def test_restarting_service_cancels_old_token_even_if_solver_finishes_late(monkeypatch):
    import threading
    import solver.solver3 as module
    from cube.cube3 import Cube3
    from solver.result import SolveResult
    started=threading.Event();release=threading.Event();answers=[];calls=[]
    def solver(_):
        calls.append(True)
        if len(calls)==1:
            started.set();assert release.wait(5)
        return SolveResult(True,[],'',0,0)
    monkeypatch.setattr(module,'solve_3x3',solver)
    service=SolveService();service.start(Cube3.solved(),lambda r:answers.append(('old',r)))
    old=service._thread
    try:
        assert started.wait(5)
        service.start(Cube3.solved(),lambda r:answers.append(('new',r)))
        service._thread.join(5)
    finally:
        release.set();old.join(5);service.cancel()
    results=dict(answers)
    assert results['new'].success
    assert not results['old'].success and results['old'].failure_kind=='cancelled'
