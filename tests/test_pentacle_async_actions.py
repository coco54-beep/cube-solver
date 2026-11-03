"""Cancelled star-cube workers must not overwrite a later entry session."""
from types import SimpleNamespace
import pytest

pytest.importorskip('kivy')
from kivy.app import App
from app.theme import Theme
from cube.pentacle import PentacleCube
import ui.screens.pentacle_screen as module


@pytest.fixture
def screen(monkeypatch):
    app=SimpleNamespace(theme=Theme(),cube=PentacleCube(),puzzle_kind='pentacle',n=3,
                        polyhedral_solution=None)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    screen=module.PentacleScreen(name='PentacleScreen')
    screen._cube=app.cube;screen.view.set_cube(app.cube)
    workers=[];callbacks=[]
    class HeldThread:
        def __init__(self,target,**kwargs):self.target=target
        def start(self):workers.append(self.target)
    monkeypatch.setattr(module,'threading',SimpleNamespace(Thread=HeldThread,Event=module.threading.Event))
    monkeypatch.setattr(module,'Clock',SimpleNamespace(schedule_once=lambda callback,*_:callbacks.append(callback)))
    yield screen,workers,callbacks
    screen._cancel_solve();screen._angle_trigger.cancel();screen.reset_interaction()


def test_finished_old_worker_does_not_clear_new_job_or_change_input(screen):
    editor,workers,callbacks=screen
    editor.randomize();workers.pop(0)()
    assert len(callbacks)==1
    editor._cancel_solve();editor.randomize();new_job=editor._job
    before=editor._cube.colors
    callbacks.pop(0)(0)
    assert editor._job is new_job and editor._cube.colors==before
    workers.pop(0)();callbacks.pop(0)(0)
    assert editor._job is None and editor._cube.colors!=before


def test_restart_does_not_reset_cancel_signal_seen_by_old_worker(screen):
    editor,workers,callbacks=screen
    editor.randomize();old_cancel=editor._cancel
    editor._cancel_solve();editor.randomize();new_job=editor._job
    assert old_cancel.is_set() and old_cancel is not editor._cancel
    workers.pop(0)()
    assert not callbacks and editor._job is new_job


def test_worker_for_replaced_cube_cannot_write_to_new_cube(screen):
    editor,workers,callbacks=screen
    editor.randomize();workers.pop(0)()
    editor._cube=PentacleCube(paints=[-1]*len(editor._cube.panels))
    before=editor._cube.colors
    callbacks.pop(0)(0)
    assert editor._job is None and editor._cube.colors==before


def test_undo_colour_edit_restores_verified_scramble_path(screen):
    from cube.polyhedral import Move
    editor,_,_=screen
    cube=editor._cube
    cube.apply_moves(cube.alignment_moves(0));cube.apply_move(Move(0,1,90))
    colours=cube.colors;history=list(cube.history)
    slot=cube.paint_slots[0];editor._color=(cube._paints[slot]+1)%6
    editor.paint(slot);assert not cube.history
    editor.undo()
    assert cube.colors==colours and cube.history==history
    cube.apply_moves(tuple(m.inverse(360) for m in reversed(cube.history)))
    assert cube.is_solved()


def test_repainting_same_colour_does_not_drop_history_or_add_undo(screen):
    from cube.polyhedral import Move
    editor,_,_=screen;cube=editor._cube
    cube.apply_move(Move(0,0,18));history=list(cube.history)
    slot=cube.paint_slots[0];editor._color=cube._paints[slot]
    editor.paint(slot)
    assert cube.history==history and not editor._history


def test_expired_scramble_budget_fallback_aligns_before_turning(screen,monkeypatch):
    editor,workers,callbacks=screen
    ticks=iter((0.,6.,6.))
    monkeypatch.setattr(module,'monotonic',lambda:next(ticks,6.))
    editor.randomize();workers.pop(0)();callbacks.pop(0)(0)
    assert editor._job is None
    assert not editor._cube.is_solved()
