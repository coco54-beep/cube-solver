"""求解页：后台求解 + 进度显示 + 取消。完成后进入回放。"""

from kivy.clock import Clock
from ui.widgets.buttons import UIButton
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from ui.widgets.dialogs import theme_popup

from app.constants import STAGE_LABEL
from app.i18n import tr
from services.solve_service import SolveService
from ui.widgets.layouts import ResponsiveBoxLayout, AdaptiveSceneLayout
from renderer.mastermorphix_view import cube_view_for


class SolvingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = SolveService()
        self._finished = False
        self._pending = None
        self._run = None

    def build_ui(self):
        root = AdaptiveSceneLayout(padding_px=[28, 16, 28, 16])
        self._scene_layout = root
        self.view = Widget()
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
        self.cancel = UIButton(text=tr("solving.cancel"))
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
        self.cancel.text = tr("solving.cancel")

    def configure(self, cube, source, on_success=None, view_factory=None, palette=None):
        """All entry screens use this page; task ownership stays here."""
        self._pending = (cube.clone(), source, on_success, view_factory, palette)

    def on_enter(self):
        if not hasattr(self, "title"):
            self.build_ui()
        pending, self._pending = self._pending, None
        if pending is None:
            pending = (_app().cube.clone(), "InputScreen", None, None, None)
        cube, self._source, self._success, factory, palette = pending
        self._finished = False
        self._cancelled = False
        run = self._run = object()
        self.title.text = tr("solving.title")
        self.progress.value = 0
        self.detail.text = tr("solving.preparing")
        self.cancel.text = tr("solving.cancel")
        self.cancel.disabled = False
        self.view = factory() if factory else cube_view_for(cube)
        self.view.lock_rotation = True
        if palette is not None:
            self.view.palette = palette
        self.view.set_cube(cube.clone())
        self._scene_layout.replace_scene(self.view)
        self.service = SolveService()
        self.service.start(
            cube,
            on_done=lambda result: Clock.schedule_once(
                lambda dt: self._finish(result, run), 0),
            on_progress=lambda payload: Clock.schedule_once(
                lambda dt, p=dict(payload): self._progress_for(run, p), 0),
        )

    def _progress_for(self, run, payload):
        if self._run is run and not self._finished and not self._cancelled:
            self._apply_progress(payload)

    def _apply_progress(self, payload):
        stage = payload.get("stage")
        label = payload.get("label")
        if "done" in payload and "total" in payload:
            done, total = payload["done"], payload["total"]
            self.detail.text = (tr("poly.optimizing") if done < 0 else
                                tr("poly.stage", done=done, total=total))
            self.progress.value = max(0, min(100, 100 * done / total)) if total > 0 and done >= 0 else 0
            return
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

    def _finish(self, result, run):
        if self._run is not run or self._finished:
            return
        self._finished = True
        if self._cancelled:
            self.manager.current = self._source
        elif result.success:
            if self._success is not None:
                self._success(result)
            else:
                _app().solve_result = result
                self.manager.current = "PlaybackScreen"
        else:
            self.manager.current = self._source
            content = Label(text=tr("poly.error.solver", detail=tr(result.message)),
                            halign="center", valign="middle", color=_app().theme.text)
            content.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
            popup = Popup(title=tr("poly.error.solve_title"), content=content,
                          size_hint=(.85, .4))
            theme_popup(popup, _app().theme)
            popup.open()

    def on_cancel(self):
        if self._finished or self._cancelled:
            return
        self._cancelled = True
        self.service.cancel()
        # Discard late callbacks even for solvers that cannot stop immediately.
        self._finished = True
        self.manager.current = self._source

    def back(self):
        self.on_cancel()

    def on_leave(self):
        self.service.cancel()
        self._run = None
        self._finished = True
        self._success = None


def _app():
    from kivy.app import App
    return App.get_running_app()
