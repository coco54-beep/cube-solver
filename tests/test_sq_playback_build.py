from types import SimpleNamespace

import pytest

pytest.importorskip("kivy")

from cube.square1 import Square1Cube
from cube.square_family import SquareFamilyCube
import ui.screens.square1_screen as square1_screen
import ui.screens.square_family_screen as square_family_screen
from ui.screens.square1_screen import Square1Screen
from ui.screens.square_family_screen import SquareFamilyScreen


class _Theme:
    text = (1, 1, 1, 1)
    text_muted = (.7, .7, .7, 1)


def _fake_app(cube):
    return SimpleNamespace(theme=_Theme(), cube=cube, simple_input=True)


def test_square1_playback_build_does_not_refresh_before_track(monkeypatch):
    cube = Square1Cube.solved()
    app = _fake_app(cube)
    monkeypatch.setattr(square1_screen, "_app", lambda: app)
    screen = Square1Screen()
    screen._playback = True
    screen._moves = ()
    screen._work = cube
    screen._build()
    assert hasattr(screen, "track")


@pytest.mark.parametrize("kind", ("square0", "square2", "super_square1"))
def test_square_family_playback_build_and_randomize(monkeypatch, kind):
    cube = SquareFamilyCube.solved(kind)
    app = _fake_app(cube)
    monkeypatch.setattr(square1_screen, "_app", lambda: app)
    monkeypatch.setattr(square_family_screen, "_app", lambda: app)
    screen = SquareFamilyScreen()
    screen._cube = cube
    screen._entry = square_family_screen.SquareFamilyEntry(cube)
    screen._playback = True
    screen._moves = ()
    screen._work = cube
    screen._build()
    assert hasattr(screen, "track")
    screen._playback = False
    screen.randomize()
    assert screen._entry.puzzle_kind == kind
