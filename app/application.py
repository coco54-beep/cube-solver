"""Kivy 应用主入口。

屏幕流程：
    HomeScreen -> InputScreen -> SolvingScreen -> PlaybackScreen

共享状态：
    self.cube: 当前 4x4/3x3 魔方逻辑状态（Cube4 / Cube3）
    self.n:    阶数 (3 或 4)
    self.solve_result: 最近一次求解结果（SolveResult）
"""

import os

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager

from app.constants import APP_NAME
from app.fonts import setup_cjk_font
from app import i18n
from cube.cube2 import Cube2
from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.cube5 import Cube5
from app.theme import Theme, AUTO, LIGHT, DARK, resolve_dark, load_saved_mode, save_mode

_KV_PATH = os.path.join(os.path.dirname(__file__), "..", "ui", "kv", "app.kv")


class CubeApp(App):
    title = APP_NAME

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        setup_cjk_font()
        # ---- 语言（须在构建屏幕前确定，屏幕文案按当前语言生成）----
        self.lang = i18n.init()
        self.title = i18n.tr("app.name")
        self.n = 4
        self.cube = Cube4.solved()
        self.solve_result = None
        self.facelets_input = None  # 用户录入的 facelets
        self._kv_loaded = False
        # ---- 主题 ----
        self.theme = Theme()
        self.theme_mode = load_saved_mode()
        self.is_dark = True
        self.theme.apply(True)
        self._apply_theme_mode()

    def build(self):
        # 惰性加载 KV：保证在 App 上下文中
        if not self._kv_loaded:
            Builder.load_file(_KV_PATH)
            self._kv_loaded = True
        sm = ScreenManager()
        for name in ("HomeScreen", "InputScreen", "SolvingScreen", "PlaybackScreen",
                     "DemoScreen", "DemoMenuScreen", "TwistScreen", "SettingsScreen"):
            scr = _screen(name)
            scr.name = name
            sm.add_widget(scr)
        return sm

    def on_start(self):
        # 后台预热求解器资源（kociemba 表 / 中心 setup 表等），消除首解长等待。
        try:
            from app.warmup import warmup_solvers
            warmup_solvers()
        except Exception:
            pass

    # ---- 共享操作 ----
    def new_cube(self, n: int):
        """新建一个已还原的 n 阶魔方，重置求解结果。"""
        self.n = n
        if n == 2:
            self.cube = Cube2.solved()
        elif n == 4:
            self.cube = Cube4.solved()
        elif n == 5:
            self.cube = Cube5.solved()
        else:
            self.cube = Cube3.solved()
        self.solve_result = None
        self.facelets_input = None

    def set_cube(self, cubies, n: int):
        """设置逻辑状态（用于从录入恢复）。"""
        self.n = n
        if n == 2:
            self.cube = Cube2(cubies)
        elif n == 4:
            self.cube = Cube4(cubies)
        elif n == 5:
            self.cube = Cube5(cubies)
        else:
            self.cube = Cube3(cubies)
        self.solve_result = None


    def _apply_theme_mode(self):
        """根据当前 theme_mode（auto/light/dark）解析深浅并应用到 Theme。"""
        self.is_dark = resolve_dark(self.theme_mode)
        self.theme.apply(self.is_dark)
        self._refresh_screens()

    def set_theme_mode(self, mode: str):
        """设置主题模式（auto/light/dark），持久化并实时生效。"""
        if mode not in (AUTO, LIGHT, DARK):
            return
        self.theme_mode = mode
        save_mode(mode)
        self._apply_theme_mode()

    # ---- 语言 ----
    def set_language(self, lang: str):
        """切换界面语言，持久化并让所有屏幕重新取词。"""
        if lang not in i18n.LANGUAGES:
            return
        self.lang = lang
        i18n.set_language(lang)
        i18n.save_language(lang)
        self.title = i18n.tr("app.name")
        self._retranslate_screens()

    def cycle_language(self):
        self.set_language(i18n.cycle_language(self.lang))

    def _retranslate_screens(self):
        """通知所有已构建的屏幕按新语言重设文案。"""
        sm = getattr(self, "root", None)
        if sm is None:
            return
        screens = list(getattr(sm, "screens", [])) or list(sm.children)
        for scr in screens:
            fn = getattr(scr, "retranslate", None)
            if fn:
                try:
                    fn()
                except Exception:
                    pass

    def _refresh_screens(self):
        """通知所有已构建的屏幕刷新其 Python 端颜色。"""
        sm = getattr(self, "root", None)
        if sm is None:
            return
        screens = list(getattr(sm, "screens", [])) or list(sm.children)
        for scr in screens:
            fn = getattr(scr, "refresh_theme", None)
            if fn:
                try:
                    fn()
                except Exception:
                    pass


def _screen(name):
    """按类名实例化屏幕。"""
    mod = __import__("ui.screens", fromlist=[name])
    cls = getattr(mod, name)
    return cls()


def main():
    CubeApp().run()


if __name__ == "__main__":
    main()
