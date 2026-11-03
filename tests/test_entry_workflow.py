"""Real-page ownership: validation, failure, cancellation and late callbacks."""
import os
from types import SimpleNamespace
import pytest

os.environ.setdefault('KIVY_NO_ARGS','1')
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.app import App
from kivy.clock import Clock
from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition,Screen,ScreenManager
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from app.theme import Theme
from cube.cube3 import Cube3
from solver.result import SolveResult
from services.solve_service import SolveService,_make_failure
from ui.screens.entry_mixin import EntryActionsMixin
from ui.screens.solving_screen import SolvingScreen
from ui.widgets.entry_controls import entry_actions


class Preview(Widget):
    def set_cube(self,cube):self.cube=cube


class Source(EntryActionsMixin,Screen):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        from kivy.uix.label import Label
        self.status=Label(text='ready');self.add_widget(self.status)
        self.row,self.buttons=entry_actions(randomize=self.randomize,clear=lambda:None,
            undo=lambda:None,assign=lambda:None,solve=lambda:None)
        self.add_widget(self.row)
    def randomize(self):self._job=object()


def pump():
    for _ in range(3):Clock.tick()


@pytest.fixture
def workflow(monkeypatch):
    app=SimpleNamespace(theme=Theme(),cube=Cube3.solved(),solve_result=None)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    manager=ScreenManager(transition=NoTransition())
    source=Source(name='Source');target=Screen(name='Other');solving=SolvingScreen(name='SolvingScreen')
    manager.add_widget(source);manager.add_widget(target);manager.add_widget(solving)
    calls=[]
    monkeypatch.setattr(SolveService,'start',lambda self,cube,**kw:calls.append((self,cube,kw)))
    pump()
    yield app,manager,source,solving,calls
    solving.service.cancel();source.entry_state.cancel();pump()


def start(workflow,**kwargs):
    app,manager,source,solving,calls=workflow
    solving.configure(app.cube,source.name,view_factory=Preview,**kwargs)
    manager.current=solving.name;pump()
    return solving._run


def test_solver_failure_returns_inline_without_popup_and_keeps_input(workflow):
    app,manager,source,solving,calls=workflow;before=app.cube.clone().cubies
    run=start(workflow)
    assert solving.operation.phase=='solving' and not solving.cancel.disabled
    assert source.row.disabled
    solving._finish(SolveResult(False,[],'internal failure',0,0),run);pump()
    assert manager.current==source.name and source._entry_notice['kind']=='solver'
    assert 'internal failure' in source.status.text and app.cube.cubies==before
    assert not source.row.disabled and solving.cancel.disabled
    assert not any(isinstance(w,Popup) and w._is_open for w in Window.children)


@pytest.mark.parametrize('action',('cancel','back','external'))
def test_cancel_back_and_external_switch_invalidate_old_result(workflow,action):
    app,manager,source,solving,calls=workflow;run=start(workflow)
    if action=='cancel':solving.on_cancel()
    elif action=='back':solving.back()
    else:manager.current='Other'
    pump();expected=manager.current
    solving._finish(SolveResult(True,[],'',0,0),run)
    solving._progress_for(run,{'progress':1.})
    assert manager.current==expected and app.solve_result is None
    assert solving._run is None and solving.cancel.disabled
    assert solving.operation.phase=='idle'
    manager.current=source.name;pump()
    assert not source.row.disabled and source.entry_can_edit()


def test_pending_cancel_never_starts_worker_and_does_not_lock_source(workflow):
    app,manager,source,solving,calls=workflow
    solving.configure(app.cube,source.name,view_factory=Preview)
    assert source.row.disabled and not solving.cancel.disabled
    solving.on_cancel();solving.on_enter();pump()
    assert not calls and not source.row.disabled


def test_factory_startup_failure_returns_to_editable_source(workflow):
    app,manager,source,solving,calls=workflow
    def bad():raise RuntimeError('preview failed')
    solving.configure(app.cube,source.name,view_factory=bad)
    manager.current=solving.name;pump()
    assert manager.current==source.name and not calls
    assert source._entry_notice['kind']=='solver' and not source.row.disabled


def test_async_scramble_cancel_switch_and_restart_restore_controls(workflow):
    app,manager,source,solving,calls=workflow
    source.buttons['random'].dispatch('on_release');old=source._job
    assert source.entry_state.phase=='scrambling' and source.row.disabled
    manager.current='Other';pump()
    assert source._job is None and source.row.disabled
    manager.current=source.name;pump();assert not source.row.disabled
    source.buttons['random'].dispatch('on_release');latest=source._job
    assert latest is not old and not source.entry_state.finish(old)
    assert source.row.disabled
    source.entry_state.finish(latest);assert not source.row.disabled


def test_source_replacement_releases_previous_pending_reservation(workflow):
    app,manager,source,solving,calls=workflow
    solving.configure(app.cube,source.name,view_factory=Preview)
    solving.configure(app.cube,'Other',view_factory=Preview)
    assert not source.row.disabled
    solving.on_cancel()


def test_error_categories_keep_internal_failure_separate_from_input():
    assert _make_failure(RuntimeError('broken')).failure_kind=='solver'
    assert _make_failure(InterruptedError()).failure_kind=='cancelled'


def test_switch_invalidates_at_start_of_transition(workflow):
    from kivy.uix.screenmanager import SlideTransition
    app,manager,source,solving,calls=workflow;old=start(workflow)
    manager.transition=SlideTransition(duration=.5)
    manager.current='Other'
    # on_leave has not fired yet. Queued progress/cancel must already be inert.
    assert manager.transition.is_active and solving._run is None
    solving.on_cancel();solving._progress_for(old,{'progress':1.})
    solving._finish(SolveResult(True,[],'',0,0),old)
    assert manager.current=='Other' and solving.cancel.disabled
    manager.transition.stop()


def test_repeated_enter_event_does_not_start_second_worker(workflow):
    app,manager,source,solving,calls=workflow;old=start(workflow)
    solving.on_enter();assert len(calls)==1 and solving._run is old
    solving.on_cancel()


def test_scramble_dispatch_exception_is_inline_and_unlocks_controls(workflow):
    from types import MethodType
    from ui.widgets.buttons import UIButton
    from ui.widgets.entry_controls import bind_random_action
    _,_,source,_,_=workflow
    def fail(self):
        self._job=object()
        raise RuntimeError('scramble preparation failed')
    button=UIButton();bind_random_action(button,MethodType(fail,source))
    button.dispatch('on_release')
    assert source._job is None and not button.disabled and not source.row.disabled
    assert source._entry_notice['kind']=='operation'


from tests.test_mixup_input_screen import editor as mixup_editor
from cube.articulated import MIXUP_MODELS


@pytest.mark.parametrize('kind',tuple(MIXUP_MODELS))
def test_empty_mixup_is_input_feedback_without_starting_worker(mixup_editor,kind):
    from copy import deepcopy
    screen=mixup_editor(kind,[]);screen.clear();before=deepcopy(screen._mx_state)
    screen.solve()
    assert screen._entry_notice['kind']=='input'
    assert screen._job is None and screen.entry_can_edit()
    assert screen._mx_state==before


def test_clone_preparation_failure_does_not_reserve_or_navigate(workflow):
    _,manager,source,solving,calls=workflow
    def broken_clone():raise RuntimeError('cannot prepare state')
    accepted=solving.configure(SimpleNamespace(clone=broken_clone),source.name)
    assert accepted is False and manager.current==source.name and not calls
    assert source._entry_notice['kind']=='operation'
    assert source.entry_can_edit() and not source.row.disabled


def test_busy_parent_preserves_disabled_undo_on_completion(workflow):
    _,_,source,_,_=workflow
    source.buttons['undo'].disabled=True
    source.buttons['random'].dispatch('on_release')
    assert source.row.disabled
    source._job=None
    assert not source.row.disabled and not source.buttons['random'].disabled
    assert source.buttons['undo'].disabled


def test_inline_error_wraps_and_restores_normal_height():
    from kivy.uix.label import Label
    from ui.entry_feedback import show_feedback
    label=Label(size_hint_y=None,height=30,width=180)
    show_feedback(label,'A detailed validation explanation that needs several lines. '*4)
    assert label.height>30 and label.height>=label.texture_size[1]
    label.text='ready'
    assert label.height==30


def test_leaving_busy_entry_has_no_transient_unlock(workflow):
    _,manager,source,_,_=workflow
    source.buttons['random'].dispatch('on_release')
    changes=[];source.entry_state.bind(locked=lambda _,value:changes.append(value))
    manager.current='Other'
    assert source.row.disabled and False not in changes


def test_failed_replacement_releases_old_pending_request(workflow):
    app,_,source,solving,calls=workflow
    solving.configure(app.cube,source.name,view_factory=Preview)
    assert source.row.disabled
    def broken():raise RuntimeError('cannot clone replacement')
    assert solving.configure(SimpleNamespace(clone=broken),source.name) is False
    assert not source.row.disabled and solving._pending is None
    solving.on_enter();assert not calls
