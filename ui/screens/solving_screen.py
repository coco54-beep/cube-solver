"""求解页：后台求解 + 进度显示 + 取消。完成后进入回放。"""

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from ui.widgets.buttons import UIButton
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.progressbar import ProgressBar

from app.constants import STAGE_LABEL
from app.i18n import tr
from services.solve_service import SolveService, CancelToken
from ui.widgets.layouts import ResponsiveBoxLayout, AdaptiveSceneLayout
from renderer.mastermorphix_view import cube_view_for


class SolvingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = SolveService()
        self._finished = False

    def build_ui(self):
        root = AdaptiveSceneLayout(padding_px=[28, 16, 28, 16])
        self._scene_layout = root
        self.view = cube_view_for(_app().cube)
        self.view.lock_rotation = True
        self._puzzle_kind = getattr(_app().cube, "puzzle_kind", "cube")
        panel = ResponsiveBoxLayout(orientation="vertical", gap_px=16, size_hint_y=None)
        title_row = ResponsiveBoxLayout(height_px=64)
        self.title = Label(text=tr("solving.title"), font_size="24sp", halign="center")
        title_row.add_widget(self.title)
        progress_row = ResponsiveBoxLayout(height_px=24)
        self.progress = ProgressBar(max=100, value=0)
        progress_row.add_widget(self.progress)
        detail_row = ResponsiveBoxLayout(height_px=92)
        self.detail = Label(text=tr("solving.preparing"), font_size="17sp", halign="center")
        self.detail.bind(size=lambda widget, *_: setattr(widget, "text_size", widget.size))
        detail_row.add_widget(self.detail)
        self.cancel = UIButton(text="", icon_name="cancel")
        self.cancel.bind(on_release=lambda *a: self.on_cancel())
        panel.add_widget(title_row)
        panel.add_widget(progress_row)
        panel.add_widget(detail_row)
        cancel_row = ResponsiveBoxLayout(height_px=52)
        cancel_row.add_widget(self.cancel)
        panel.add_widget(cancel_row)
        root.set_content(self.view, panel)
        self.add_widget(root)

    def retranslate(self):
        if not hasattr(self, "title"):
            return
        self.title.text = tr("solving.title")

    def on_enter(self):
        if not hasattr(self, "title"):
            self.build_ui()
        self._finished = False
        self.title.text = tr("solving.title")
        self.progress.value = 0
        self.detail.text = tr("solving.preparing")
        app = _app()
        kind = getattr(app.cube, "puzzle_kind", "cube")
        if kind != self._puzzle_kind:
            self.view = cube_view_for(app.cube)
            self.view.lock_rotation = True
            self._scene_layout.replace_scene(self.view)
            self._puzzle_kind = kind
        self.view.set_cube(app.cube.clone())
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
        label = payload.get("label")
        if label:
            self.detail.text = tr(label)
        elif stage in STAGE_LABEL:
            self.detail.text = tr(STAGE_LABEL[stage])
        elif "paired" in payload:
            self.detail.text = tr("solving.pairing", done=payload["paired"])
        elif "depth" in payload:
            self.detail.text = tr("solving.depth", depth=payload["depth"])
        progress = payload.get("progress")
        if progress is not None:
            self.progress.value = max(0, min(100, int(progress * 100)))
            return
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
        self.detail.text = tr("solving.cancelling")

    def on_leave(self):
        pass


def _app():
    from kivy.app import App
    return App.get_running_app()
