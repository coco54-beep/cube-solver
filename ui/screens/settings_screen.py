"""设置页：主题（自动/浅色/深色）、语言（简中/英/日）与关于信息。

偏好统一由 app 层持久化并实时生效：
    * 主题 -> app.set_theme_mode(mode)（触发各屏 refresh_theme）
    * 语言 -> app.set_language(lang)（触发各屏 retranslate）
选中项以绿色 PrimaryButton 高亮，其余为普通 UIButton。
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from app import i18n
from app.config import Config
from app.i18n import tr
from app.theme import AUTO, LIGHT, DARK
from ui.widgets.buttons import PrimaryButton, UIButton

_THEME_ORDER = (AUTO, LIGHT, DARK)


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    # ---- 构建 ----
    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=10, padding=[16, 12, 16, 12])

        top = BoxLayout(size_hint_y=None, height=46, spacing=8)
        self.btn_back = UIButton(text=tr("input.back"), size_hint_x=0.24)
        self.btn_back.bind(on_release=lambda *a: self.go_home())
        self.lbl_title = Label(text=tr("settings.title"), size_hint_x=0.76,
                               halign="center", bold=True, font_size="22sp")
        top.add_widget(self.btn_back)
        top.add_widget(self.lbl_title)
        root.add_widget(top)

        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", spacing=10,
                            size_hint_y=None, padding=[2, 6, 2, 6])
        content.bind(minimum_height=content.setter("height"))
        scroll.add_widget(content)
        root.add_widget(scroll)

        # 主题
        self.lbl_theme = self._section_label(tr("settings.theme"))
        content.add_widget(self.lbl_theme)
        self.theme_row = BoxLayout(spacing=8, size_hint_y=None, height=52)
        content.add_widget(self.theme_row)

        # 语言
        self.lbl_lang = self._section_label(tr("settings.language"))
        content.add_widget(self.lbl_lang)
        self.lang_row = BoxLayout(spacing=8, size_hint_y=None, height=52)
        content.add_widget(self.lang_row)

        # 关于
        self.lbl_about = self._section_label(tr("settings.about"))
        content.add_widget(self.lbl_about)
        self.lbl_app = Label(text=tr("app.name"), font_size="17sp", bold=True,
                             halign="center", size_hint_y=None)
        self.lbl_ver = Label(text=tr("home.version", version=Config.app_version),
                             font_size="14sp", color=_app().theme.text_muted,
                             halign="center", size_hint_y=None)
        self.lbl_tagline = Label(text=tr("settings.about_tagline"), font_size="14sp",
                                 halign="center", size_hint_y=None)
        for w in (self.lbl_app, self.lbl_ver, self.lbl_tagline):
            w.bind(width=lambda lbl, s: setattr(lbl, "text_size", (s, None)))
            w.bind(texture_size=lambda lbl, ts: setattr(lbl, "height", ts[1] + 2))
            content.add_widget(w)

        self.add_widget(root)
        self._build_theme_row()
        self._build_lang_row()

    def _section_label(self, text):
        lbl = Label(text=text, font_size="15sp", bold=True, halign="left",
                    size_hint_y=None, height=30)
        lbl.color = _app().theme.accent
        return lbl

    # ---- 主题 ----
    def _build_theme_row(self):
        self.theme_row.clear_widgets()
        current = _app().theme_mode
        for mode in _THEME_ORDER:
            self.theme_row.add_widget(
                self._option(tr(f"theme.{mode}"), mode == current,
                             lambda m=mode: self.pick_theme(m)))

    def pick_theme(self, mode):
        _app().set_theme_mode(mode)
        self._build_theme_row()

    # ---- 语言 ----
    def _build_lang_row(self):
        self.lang_row.clear_widgets()
        current = i18n.current_language()
        for lang in i18n.LANGUAGES:
            self.lang_row.add_widget(
                self._option(i18n.LANGUAGE_NAMES.get(lang, lang), lang == current,
                             lambda lg=lang: self.pick_language(lg)))

    def pick_language(self, lang):
        _app().set_language(lang)

    def _option(self, label, selected, on_pick):
        cls = PrimaryButton if selected else UIButton
        btn = cls(text=label)
        btn.bind(on_release=lambda *a: on_pick())
        return btn

    # ---- 生命周期 ----
    def retranslate(self):
        if not hasattr(self, "lbl_title"):
            return
        self.btn_back.text = tr("input.back")
        self.lbl_title.text = tr("settings.title")
        self.lbl_theme.text = tr("settings.theme")
        self.lbl_lang.text = tr("settings.language")
        self.lbl_about.text = tr("settings.about")
        self.lbl_app.text = tr("app.name")
        self.lbl_ver.text = tr("home.version", version=Config.app_version)
        self.lbl_tagline.text = tr("settings.about_tagline")
        self._build_theme_row()
        self._build_lang_row()

    def refresh_theme(self):
        if not hasattr(self, "lbl_title"):
            return
        self.lbl_title.color = _app().theme.text
        for lbl in (self.lbl_theme, self.lbl_lang, self.lbl_about):
            lbl.color = _app().theme.accent
        self.lbl_ver.color = _app().theme.text_muted
        self._build_theme_row()
        self._build_lang_row()

    def go_home(self):
        self.manager.current = "HomeScreen"


def _app():
    from kivy.app import App
    return App.get_running_app()
