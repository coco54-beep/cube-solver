"""Polyhedral solve validates input before leaving the entry screen."""

import pytest

pytest.importorskip("kivy")


def test_incomplete_polyhedral_stays_on_entry_screen():
    try:
        from app.application import CubeApp
        app = CubeApp()
        app.root = app.build()
    except Exception as exc:
        pytest.skip("no Kivy window: %s" % exc)

    app.new_polyhedral("fto", 3)
    screen = app.root.get_screen("PolyhedralScreen")
    screen.on_pre_enter()
    screen.on_enter()
    app.root.current = "PolyhedralScreen"
    screen._cube.colors[0] = -1
    errors = []
    screen.error = errors.append

    screen.solve()

    assert app.root.current == "PolyhedralScreen"
    assert errors == ["Please enter every sticker"]
