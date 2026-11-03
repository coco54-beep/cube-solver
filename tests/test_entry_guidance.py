"""Guidance stays in help; real validation messages remain visible."""
from types import SimpleNamespace

from tests.test_bandaged_manual_controls import pump
from kivy.app import App
from app.theme import Theme
from cube.mastermorphix import DEFAULT_PALETTE
from ui.entry_feedback import show_feedback
from ui.widgets.entry_guidance import EntryGuidance
from ui.screens.mastermorphix_screen import MastermorphixScreen
from ui.screens.twist_screen import TwistScreen
from ui.screens.polyhedral_screen import PolyhedralTwistScreen


def test_guidance_is_hidden_through_refresh_but_feedback_wraps():
    hint=EntryGuidance(text='Choose a colour, then tap a face.', width=160)
    hint.height=54;hint.opacity=1
    assert hint.height==0 and hint.opacity==0
    assert hint.text=='Choose a colour, then tap a face.'
    show_feedback(hint,'Missing colours: complete the highlighted pieces before solving.')
    assert hint.opacity==1 and hint.height>0
    original_height=hint.height
    hint.width=85
    assert hint.height>original_height
    hint.text='Choose a piece and turn it.'
    assert hint.height==0 and hint.opacity==0
    show_feedback(hint,'Try again.')
    assert hint.height>0 and hint.opacity==1


def test_piece_entry_still_displays_validation_errors(monkeypatch):
    app=SimpleNamespace(theme=Theme(),n=2,mastermorphix_palette=DEFAULT_PALETTE,
                        cube=None,simple_input=False)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    screen=MastermorphixScreen()
    screen.on_pre_enter();pump()
    assert screen.hint.text and screen.hint.height==0 and screen.hint.opacity==0
    assert screen.check() is None
    assert screen._entry_notice['category']=='incomplete'
    assert screen.hint.height>0 and screen.hint.opacity==1
    screen._resize();pump()
    assert screen.hint.height>0 and screen.hint.opacity==1
    screen._refresh();pump()
    assert screen.hint.height==0 and screen.hint.opacity==0
    screen.reset_interaction()


def test_blocked_turns_still_display_feedback():
    hint=EntryGuidance(text='Drag to turn.')
    screen=SimpleNamespace(_busy=False,msg=hint,
        _work=SimpleNamespace(can_turn=lambda *_:False))
    TwistScreen._twist(screen,SimpleNamespace(axis=0,layer_positions=(1,),sign=1))
    assert hint.text and hint.opacity==1 and hint.height>0
    hint=EntryGuidance(text='Select a layer.')
    screen=SimpleNamespace(hint=hint,
        view=SimpleNamespace(_move=None,camera_busy=False),
        _cube=SimpleNamespace(rigid_family=True,puzzle_kind='pentacle',can_apply=lambda *_:False))
    PolyhedralTwistScreen.twist(screen,None)
    assert hint.text and hint.opacity==1 and hint.height>0
