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
from cube.cube_n import CubeN
from app.theme import Theme, AUTO, LIGHT, DARK, resolve_dark, load_saved_mode, save_mode
from app.prefs import get as _pref_get, set as _pref_set
from app.mastermorphix_palette import load_palette
from cube.mastermorphix import MastermorphixCube

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
        self.puzzle_kind = "cube"
        self.mastermorphix_palette = load_palette()
        self.solve_result = None
        self.facelets_input = None  # 用户录入的 facelets
        self.facelets_cache = {}    # 各阶录入状态的快照（切回该阶时恢复）
        self.input_from_camera = False  # 录入页是否由拍照识别进入（决定返回目标）
        self.camera_return_screen = 'HomeScreen'
        self.camera_shape_result = None
        self.camera_recorded = None
        # ---- 输入方式（高级 / 简洁，默认简洁）----
        self.simple_input = bool(_pref_get("simple_input", True))
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
        for name in ("HomeScreen", "InputScreen", "CameraScreen", "MastermorphixScreen", "MirrorScreen", "MorphixTwistScreen", "PolyhedralScreen", "PolyhedralTwistScreen", "PolyhedralPlaybackScreen", "SolvingScreen", "PlaybackScreen",
                     "DemoScreen", "DemoMenuScreen", "FormulaLibraryScreen", "PracticeScreen",                      "TwistScreen", "SettingsScreen", "Square1Screen", "ShapeCubeScreen", "MirrorTowerScreen",
                     "MirrorWindmillScreen", "MirrorAxisScreen", "MirrorFisherScreen", "MirrorUnequalWindmillScreen", "MirrorUnequalFisherScreen", "MirrorOffsetWindmillScreen", "MirrorOffsetFisherScreen", "MirrorPyraminxScreen", "MirrorSkewbScreen", "GhostScreen", "GhostTwistScreen", "SquareFamilyScreen"):
            scr = _screen(name)
            scr.name = name
            sm.add_widget(scr)
        return sm

    def on_start(self):
        # 设备端求解基准（adb extra / 环境变量），跑完即退出。
        try:
            from app.device_bench import requested as bench_spec, run as bench_run
            spec=bench_spec()
            if spec:
                from kivy.clock import Clock
                def _bench(_dt):
                    try:
                        bench_run(spec)
                    except Exception:
                        try:
                            from kivy.logger import Logger
                            Logger.exception("device_bench failed")
                        except Exception:
                            pass
                    finally:
                        self.stop()
                Clock.schedule_once(_bench, 0.5)
                return
        except Exception:
            pass
        # 若请求了 UI 自检（adb extra / 环境变量），跑完即退出，不做求解预热。
        try:
            from app.ui_self_check import requested, default_output_dir, UISelfCheck
            if requested():
                out = default_output_dir()

                def _done(data):
                    try:
                        from kivy.logger import Logger
                        Logger.info("ui_selfcheck: %s (%d checked, %d errors) -> %s"
                                    % (data.get("status"), data.get("checked"),
                                       data.get("errors"), out))
                    except Exception:
                        pass
                    self.stop()

                # 必须持有引用：Kivy Clock 对绑定方法只留弱引用，否则会被回收。
                self._ui_selfcheck = UISelfCheck(self, out, on_done=_done)
                self._ui_selfcheck.start()
                return
        except Exception:
            try:
                import traceback
                from kivy.logger import Logger
                Logger.error("ui_selfcheck setup failed:\n" + traceback.format_exc())
            except Exception:
                pass
        from app.session import SessionStore
        from kivy.clock import Clock
        self._session_store = SessionStore(self)
        self._session_store.restore()
        self._autosave_event = Clock.schedule_interval(lambda _dt: self._session_store.save(), 5)
        # 后台预热求解器资源（kociemba 表 / 中心 setup 表等），消除首解长等待。
        try:
            from app.warmup import warmup_solvers
            warmup_solvers()
        except Exception:
            pass

    # ---- 共享操作 ----
    def _reset_input_interaction(self):
        sm = getattr(self, "root", None)
        if sm is not None:
            for name in ("InputScreen", "MastermorphixScreen", "MirrorScreen", "PolyhedralScreen",
                         "MorphixTwistScreen", "GhostTwistScreen", "PolyhedralTwistScreen", "Square1Screen", "SquareFamilyScreen", "ShapeCubeScreen", "MirrorTowerScreen", "MirrorPyraminxScreen", "MirrorSkewbScreen"):
                if sm.has_screen(name):
                    self._screen_lifecycle(sm.get_screen(name), "reset_interaction")

    @staticmethod
    def _screen_lifecycle(screen, method):
        callback = getattr(screen, method, None)
        if callback is None:
            return
        try:
            callback()
        except Exception:
            from kivy.logger import Logger
            Logger.exception("Lifecycle: %s.%s failed", screen.name, method)

    def on_pause(self):
        store = getattr(self, '_session_store', None)
        if store is not None: store.save(synchronous=True)
        self._reset_input_interaction()
        if self.root is not None and self.root.has_screen("CameraScreen"):
            self._screen_lifecycle(self.root.get_screen("CameraScreen"), "pause_camera")
        import gc
        gc.collect()
        # A failed cleanup must never make Kivy treat backgrounding as an exit.
        return True

    def on_resume(self):
        self._reset_input_interaction()
        if self.root is not None and self.root.has_screen("CameraScreen"):
            self._screen_lifecycle(self.root.get_screen("CameraScreen"), "resume_camera")
        # A static photo may produce no new frames after SDL resumes. Reattach
        # the retained screen canvas to refresh SDL's surface instructions;
        # asking for a redraw alone can leave this screen entirely black.
        from kivy.clock import Clock
        def redraw(_dt):
            if self.root is not None:
                screen = getattr(self.root, 'current_screen', None)
                transition = getattr(self.root, 'transition', None)
                if screen is not None and not getattr(transition, 'is_active', False):
                    canvas = screen.canvas
                    if canvas in self.root.canvas.children:
                        index = self.root.canvas.children.index(canvas)
                        self.root.canvas.remove(canvas)
                        self.root.canvas.insert(index, canvas)
                self.root.canvas.ask_update()
            from kivy.core.window import Window
            Window.canvas.ask_update()
        # Timers queued during pause may all fire on the first resumed tick.
        # Cross a frame boundary after that tick before remounting the canvas.
        Clock.schedule_once(lambda _dt: Clock.schedule_once(redraw, 0), .3)

    def on_stop(self):
        event = getattr(self, '_autosave_event', None)
        if event is not None: event.cancel()
        store = getattr(self, '_session_store', None)
        if store is not None: store.save(synchronous=True)

    def new_cube(self, n: int):
        """新建一个已还原的 n 阶魔方，重置求解结果。"""
        self.n = n
        self.puzzle_kind = "cube"
        if n == 2:
            self.cube = Cube2.solved()
        elif n == 4:
            self.cube = Cube4.solved()
        elif n == 5:
            self.cube = Cube5.solved()
        elif n >= 6:
            self.cube = CubeN.solved(n)
        else:
            self.cube = Cube3.solved()
        self.solve_result = None
        self.facelets_input = None

    def new_mastermorphix(self, n=3):
        self.n = n
        self.puzzle_kind = "mastermorphix"
        self.cube = MastermorphixCube.solved(self.mastermorphix_palette, n)
        self.solve_result = None
        self.facelets_input = None

    def set_cube(self, cubies, n: int):
        """设置逻辑状态（用于从录入恢复）。"""
        self.n = n
        self.puzzle_kind = "cube"
        if n == 2:
            self.cube = Cube2(cubies)
        elif n == 4:
            self.cube = Cube4(cubies)
        elif n == 5:
            self.cube = Cube5(cubies)
        elif n >= 6:
            self.cube = CubeN(cubies, n)
        else:
            self.cube = Cube3(cubies)
        self.solve_result = None

    def new_polyhedral(self, kind, n):
        from cube.polyhedral import PolyhedralPuzzle
        self.n = n
        self.cube = PolyhedralPuzzle(kind, n)
        self.puzzle_kind = self.cube.puzzle_kind
        self.cube.colors = [-1] * len(self.cube.colors)
        self.polyhedral_solution = None

    def new_mirror(self, n=3):
        from cube.mirror import MirrorCube
        self.n = n
        self.puzzle_kind = 'mirror'
        self.cube = MirrorCube.solved(n=n)
        self.solve_result = None

    def new_square1(self):
        from cube.square1 import Square1Cube
        self.n=3
        self.puzzle_kind='square1'
        self.cube=Square1Cube.solved()
        self.solve_result=None

    def new_square_family(self, kind='square0'):
        from cube.square_family import SquareFamilyCube
        self.n=3
        self.puzzle_kind=kind
        self.cube=SquareFamilyCube.solved(kind)
        self.solve_result=None

    def new_mirror_tower(self):
        from cube.mirror_tower import MirrorTowerCube
        self.n=3
        self.puzzle_kind='mirror_tower'
        self.cube=MirrorTowerCube.solved()
        self.polyhedral_solution=None

    def new_mirror_pyraminx(self, n=3):
        from cube.mirror_pyraminx import MirrorPyraminxCube
        self.cube=MirrorPyraminxCube.solved(n=n)
        self.n=n
        self.puzzle_kind='mirror_pyraminx'
        self.polyhedral_solution=None

    def new_mirror_skewb(self):
        from cube.mirror_skewb import MirrorSkewbCube
        self.cube=MirrorSkewbCube.solved()
        self.n=3
        self.puzzle_kind='mirror_skewb'
        self.polyhedral_solution=None

    def new_ghost(self, n=3):
        from cube.ghost import GhostCube
        self.cube=GhostCube.solved(n=n)
        self.n=n
        self.puzzle_kind='ghost'
        self.solve_result=None

    def new_shape_cube(self,kind='axis',n=3):
        from cube.shape_cube import AxisCube,PandoraCube,WindmillCube,FisherCube
        factories={'axis':AxisCube,'pandora':PandoraCube,'windmill':WindmillCube,'fisher':FisherCube}
        if kind not in factories:
            raise ValueError('Unsupported shape modification')
        self.n=n
        self.puzzle_kind=kind
        self.cube=factories[kind].solved(n=n)
        self.solve_result=None

    def new_mirror_shape(self,kind='mirror_windmill',n=3):
        from cube.mirror_shape import (MirrorAxisCube, MirrorFisherCube, MirrorWindmillCube,
                                       MirrorUnequalWindmillCube, MirrorUnequalFisherCube,
                                       MirrorOffsetWindmillCube, MirrorOffsetFisherCube)
        factories={'mirror_windmill':MirrorWindmillCube,
                   'mirror_axis':MirrorAxisCube,
                   'mirror_fisher':MirrorFisherCube,
                   'mirror_windmill_unequal':MirrorUnequalWindmillCube,
                   'mirror_fisher_unequal':MirrorUnequalFisherCube,
                   'mirror_windmill_offset':MirrorOffsetWindmillCube,
                   'mirror_fisher_offset':MirrorOffsetFisherCube}
        if kind not in factories:
            raise ValueError('Unsupported mirror shape modification')
        self.n=n
        self.puzzle_kind=kind
        self.cube=factories[kind].solved(n=n)
        self.solve_result=None


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

    # ---- 输入方式（高级 / 简洁）----
    def set_input_mode(self, simple: bool):
        """切换录入页的高级/简洁输入，持久化并即时重建录入页布局。"""
        self.simple_input = bool(simple)
        _pref_set("simple_input", self.simple_input)
        sm = getattr(self, "root", None)
        if sm is None:
            return
        scr = sm.get_screen("InputScreen")
        fn = getattr(scr, "apply_input_mode", None)
        if fn:
            try:
                fn(self.simple_input)
            except Exception:
                pass

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
