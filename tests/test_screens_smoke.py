"""屏幕构造冒烟测试：无需真实 Kivy 窗口，用打桩 app/theme 构建首页与设置页。

用于捕获构造期文案/主题访问的回归（CI 无 OpenGL 窗口，无法跑真正的 App）。
"""

import pytest

pytest.importorskip("kivy")

from app import i18n


class _FakeTheme:
    def __getattr__(self, name):
        return (0.1, 0.1, 0.1, 1)

    def bind(self, **kwargs):
        pass


class _FakeApp:
    def __init__(self):
        self.theme = _FakeTheme()
        self.theme_mode = "auto"
        self.lang = i18n.current_language()
        self.screens = []

    def set_theme_mode(self, mode):
        self.theme_mode = mode
        for scr in self.screens:
            scr.refresh_theme()

    def set_language(self, lang):
        self.lang = lang
        i18n.set_language(lang)
        for scr in self.screens:
            scr.retranslate()


def _build(monkeypatch):
    import ui.screens.home_screen as hs
    import ui.screens.settings_screen as ss

    app = _FakeApp()
    monkeypatch.setattr(hs, "_app", lambda: app)
    monkeypatch.setattr(ss, "_app", lambda: app)

    home = hs.HomeScreen()
    settings = ss.SettingsScreen()
    app.screens = [home, settings]
    return app, home, settings


def test_screens_construct_and_retranslate(monkeypatch):
    app, home, settings = _build(monkeypatch)
    assert home.settings_btn.text
    assert settings.lbl_title.text

    for scr in app.screens:
        scr.retranslate()
        scr.refresh_theme()


def test_settings_apply_theme_and_language(monkeypatch):
    app, _home, settings = _build(monkeypatch)
    settings.pick_theme("dark")
    assert app.theme_mode == "dark"

    before = settings.lbl_title.text
    settings.pick_language("ja" if i18n.current_language() != "ja" else "en")
    assert settings.lbl_title.text != before
