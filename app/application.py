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
from cube.cube2 import Cube2
from cube.cube3 import Cube3
from cube.cube4 import Cube4

_KV_PATH = os.path.join(os.path.dirname(__file__), "..", "ui", "kv", "app.kv")


class CubeApp(App):
    title = APP_NAME

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        setup_cjk_font()
        self.n = 4
        self.cube = Cube4.solved()
        self.solve_result = None
        self.facelets_input = None  # 用户录入的 facelets
        self._kv_loaded = False

    def build(self):
        # 惰性加载 KV：保证在 App 上下文中
        if not self._kv_loaded:
            Builder.load_file(_KV_PATH)
            self._kv_loaded = True
        sm = ScreenManager()
        for name in ("HomeScreen", "InputScreen", "SolvingScreen", "PlaybackScreen",
                     "DemoScreen", "DemoMenuScreen"):
            scr = _screen(name)
            scr.name = name
            sm.add_widget(scr)
        return sm

    # ---- 共享操作 ----
    def new_cube(self, n: int):
        """新建一个已还原的 n 阶魔方，重置求解结果。"""
        self.n = n
        if n == 2:
            self.cube = Cube2.solved()
        elif n == 4:
            self.cube = Cube4.solved()
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
        else:
            self.cube = Cube3(cubies)
        self.solve_result = None


def _screen(name):
    """按类名实例化屏幕。"""
    mod = __import__("ui.screens", fromlist=[name])
    cls = getattr(mod, name)
    return cls()


def main():
    CubeApp().run()


if __name__ == "__main__":
    main()
