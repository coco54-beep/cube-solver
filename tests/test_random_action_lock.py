"""Scramble locks follow task-state events, without timer or _job polling."""
import pytest
from ui.entry_state import EntryTaskState
from ui.widgets.entry_controls import bind_random_action


class Button:
    disabled=False
    def bind(self,**kwargs):self.release=kwargs['on_release']


class Owner:
    def __init__(self,asynchronous):
        self.entry_state=EntryTaskState();self.asynchronous=asynchronous;self.calls=0
    def randomize(self):
        self.calls+=1
        if self.asynchronous:self.entry_state.begin('scrambling')


def test_synchronous_scramble_unlocks_immediately():
    owner=Owner(False);button=Button();bind_random_action(button,owner.randomize)
    button.release()
    assert owner.calls==1 and not button.disabled


def test_background_scramble_unlocks_on_task_completion_without_clock_tick():
    owner=Owner(True);button=Button();bind_random_action(button,owner.randomize)
    button.release();assert button.disabled
    button.release();assert owner.calls==1
    owner.entry_state.finish(owner.entry_state.token)
    assert not button.disabled


def test_cancelled_background_job_cannot_finish_a_new_scramble():
    owner=Owner(True);button=Button();bind_random_action(button,owner.randomize)
    button.release();old=owner.entry_state.token
    owner.entry_state.cancel();button.release();new=owner.entry_state.token
    assert new is not old and not owner.entry_state.finish(old)
    assert button.disabled
    owner.entry_state.finish(new);assert not button.disabled


def test_leaving_page_keeps_buttons_locked_until_return():
    owner=Owner(True);button=Button();bind_random_action(button,owner.randomize)
    button.release();owner.entry_state.active=False;owner.entry_state.cancel()
    assert button.disabled
    owner.entry_state.active=True;assert not button.disabled


def test_callback_error_releases_button():
    def bad():raise RuntimeError('failed')
    button=Button();bind_random_action(button,bad)
    with pytest.raises(RuntimeError):button.release()
    assert not button.disabled
