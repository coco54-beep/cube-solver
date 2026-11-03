"""Simple mode has essential icons only; advanced mode retains the tools."""
from types import SimpleNamespace
import pytest
from tests.test_bandaged_manual_controls import pump,until
from kivy.app import App
from kivy.core.window import Window
from app.theme import Theme
from cube.cube3 import Cube3
from ui.screens.input_screen import InputScreen
from ui.widgets.entry_controls import EntryActionRow
from ui.widgets.icons import icon_image


@pytest.fixture
def app(monkeypatch):
    app=SimpleNamespace(theme=Theme(),cube=Cube3.solved(),n=3,puzzle_kind='cube',
        simple_input=True,facelets_cache={},facelets_input=None,solve_result=None,
        bandage_entry_cache={},input_from_camera=False)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    return app


def test_simple_cube_has_no_more_menu_and_only_essentials_at_every_width(app):
    screen=InputScreen();screen.on_enter();row=screen.simple_turn_row
    row.width=350;row.reflow()
    try:
        assert screen.btn_pick.icon_name=='gear'
        assert all(b.icon_name and not b.text for b in screen.entry_action_buttons.values())
        assert not hasattr(row,'more') and not hasattr(row,'open_more')
        for width in (350,800,1200):
            row.width=width;row.reflow()
            assert list(reversed(row.children))==[row.buttons[k] for k in row.simple_keys]
            for key in ('pick','fill','redo','scramble','target'):assert row.buttons[key].parent is None
        app.simple_input=False;row.reflow()
        assert list(reversed(row.children))==list(row.buttons.values())
        assert screen.btn_pick.icon_name=='gear' and not screen.btn_pick.text
    finally:
        screen.reset_interaction()


def test_play_only_simple_actions_keep_twisting_and_reset_without_entry_tools(app):
    from ui.widgets.buttons import UIButton
    row=EntryActionRow(SimpleNamespace(play_only=True),None)
    for key in ('twist','random','clear','undo','target','solve'):row.add_action(key,UIButton(icon_name=key))
    row.hidden_keys.add('clear');row.reflow()
    assert list(reversed(row.children))==[row.buttons[k] for k in row.play_keys]
    assert row.buttons['clear'].parent is None


def test_simple_to_advanced_keeps_entry_and_icon_buttons(app):
    screen=InputScreen();screen.on_enter()
    data=screen.collect_facelets();data['F'][0][0]='G';screen.set_facelets(data)
    for simple in (False,True,False,True):
        app.simple_input=simple;screen.apply_input_mode(simple)
        assert screen.collect_facelets()==data
        assert all(getattr(screen,name).icon_name and not getattr(screen,name).text
                   for name in ('btn_pick','btn_fill','btn_undo','btn_redo','btn_random','btn_clear','btn_twist','btn_assign','btn_scramble','btn_solve'))
    screen.reset_interaction()
