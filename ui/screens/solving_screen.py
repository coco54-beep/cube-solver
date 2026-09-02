"""求解页：后台求解 + 进度显示 + 取消。完成后进入回放。"""

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.progressbar import ProgressBar

from app.constants import STAGE_LABEL
from services.solve_service import SolveService, CancelToken


class SolvingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = SolveService()
        self._finished = False

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=24, spacing=12)
        self.title = Label(text="正在求解…", font_size="24sp", size_hint_y=0.2)
        self.progress = ProgressBar(max=100, value=0, size_hint_y=0.15)
        self.detail = Label(text="准备中", font_size="17sp", size_hint_y=0.15)
        self.cancel = Button(text="取消", font_size="20sp", size_hint_y=0.15)
        self.cancel.bind(on_release=lambda *a: self.on_cancel())
        root.add_widget(self.title)
        root.add_widget(self.progress)
        root.add_widget(self.detail)
        root.add_widget(self.cancel)
        self.add_widget(root)

    def on_enter(self):
        if not hasattr(self, "title"):
            self.build_ui()
        self._finished = False
        self.title.text = "正在求解…"
        self.progress.value = 0
        self.detail.text = "准备中"
        app = _app()
        self.service.start(
            app.cube,
            on_done=self._on_done,
            on_progress=self._on_progress,
        )

    def _on_progress(self, payload):
        # 从后台线程切回 UI 线程
        Clock.schedule_once(lambda dt, p=payload: self._apply_progress(p), 0)

    def _apply_progress(self, payload):
        stage = payload.get("stage")
        if stage in STAGE_LABEL:
            self.detail.text = STAGE_LABEL[stage]
        elif "paired" in payload:
            self.detail.text = f"棱块配对 {payload['paired']}/12"
        elif "depth" in payload:
            self.detail.text = f"中心求解深度 {payload['depth']}"
        matched = payload.get("matched", payload.get("paired"))
        if matched is not None:
            self.progress.value = min(100, int(matched * 100 / 12))

    def _on_done(self, result):
        Clock.schedule_once(lambda dt, r=result: self._finish(r), 0)

    def _finish(self, result):
        if self._finished:
            return
        self._finished = True
        app = _app()
        app.solve_result = result
        self.manager.current = "PlaybackScreen"

    def on_cancel(self):
        self.service.cancel()
        self.detail.text = "正在取消…"

    def on_leave(self):
        pass


def _app():
    from kivy.app import App
    return App.get_running_app()
