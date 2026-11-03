"""求解页：后台求解 + 进度显示 + 取消。完成后进入回放。"""

from kivy.clock import Clock
from ui.widgets.buttons import UIButton
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.uix.progressbar import ProgressBar

from app.constants import STAGE_LABEL
from app.i18n import tr
from services.solve_service import SolveService
from ui.widgets.layouts import ResponsiveBoxLayout, AdaptiveSceneLayout
from renderer.mastermorphix_view import cube_view_for
from ui.entry_state import EntryTaskState


class SolvingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = SolveService()
        self._finished = False
        self._cancelled = False
        self._source = 'InputScreen'
        self._pending = None
        self._run = None
        self.operation=EntryTaskState()
        self._source_task=None

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
        metrics_row=ResponsiveBoxLayout(height_px=54)
        self.metrics=Label(font_size='13sp',halign='center',valign='middle')
        self.metrics.bind(size=lambda w,v:setattr(w,'text_size',v));metrics_row.add_widget(self.metrics)
        self.cancel = UIButton(icon_name='cancel')
        self.cancel.bind(on_release=lambda *a: self.on_cancel())
        panel.add_widget(title_row)
        panel.add_widget(progress_row)
        panel.add_widget(detail_row)
        panel.add_widget(metrics_row)
        cancel_row = ResponsiveBoxLayout(height_px=52)
        cancel_row.add_widget(self.cancel)
        panel.add_widget(cancel_row)
        root.set_content(self.view, panel)
        self.add_widget(root)

    def retranslate(self):
        if not hasattr(self, "title"):
            return
        self.title.text = tr("solving.title")
        self.cancel.text = ''

    def configure(self, cube, source, on_success=None, view_factory=None, palette=None):
        """All entry screens use this page; task ownership stays here."""
        if (self.manager is not None and self.manager.current==self.name and not self._finished
                and (self._run is not None or self._pending is not None)):
            return False
        try:snapshot=cube.clone()
        except Exception as exc:
            self._invalidate()
            if self.manager is not None and self.manager.has_screen(source):
                entry=self.manager.get_screen(source)
                if hasattr(entry,'entry_show_exception'):entry.entry_show_exception(exc)
            return False
        self.service.cancel()
        self._release_source()
        self._run = None
        self._cancelled = False
        self._finished = False
        self._source = source
        self._pending = (snapshot, source, on_success, view_factory, palette)
        self.operation.begin('preparing')
        if self.manager is not None and self.manager.has_screen(source):
            entry=self.manager.get_screen(source)
            if hasattr(entry,'entry_state'):
                token=entry.entry_state.begin('solving');self._source_task=(entry,token)
        if not hasattr(self,'title'):self.build_ui()
        self._clear_scene()
        return True

    def _clear_scene(self):
        """Remove the previous puzzle before the screen starts sliding in."""
        if not hasattr(self, "_scene_layout") or self._scene_layout.scene is None:
            return
        view = getattr(self, "view", None)
        if view is not None and hasattr(view, "cancel_animation"):
            view.cancel_animation()
        self._scene_layout.replace_scene(Widget())
        self.title.text = tr("solving.title")
        self.progress.value = 0
        self.detail.text = tr("solving.preparing")
        self.cancel.disabled = self._pending is None

    def on_pre_enter(self):
        self._clear_scene()

    def on_enter(self):
        if self._cancelled and self._pending is None:
            return
        if self._run is not None and not self._finished and self._pending is None:
            return
        if not hasattr(self, "title"):
            self.build_ui()
        pending, self._pending = self._pending, None
        if pending is None:
            pending = (_app().cube.clone(), "InputScreen", None, None, None)
        cube, self._source, self._success, factory, palette = pending
        self._finished = False
        self._cancelled = False
        run = self._run = self.operation.begin('solving')
        self.title.text = tr("solving.title")
        self.progress.value = 0
        self.detail.text = tr("solving.preparing")
        self.cancel.text = ''
        self.cancel.disabled = False
        from time import monotonic
        self._begun=monotonic();self._search_metrics={}
        if getattr(self,'_time_event',None):self._time_event.cancel()
        self._time_event=Clock.schedule_interval(self._update_time,1);self._update_time()
        try:
            self.view = factory() if factory else cube_view_for(cube)
            self.view.lock_rotation = True
            self.view.set_cube(cube.clone())
            if palette is not None:self.view.palette = tuple(palette)
            self._scene_layout.replace_scene(self.view)
            self.service = SolveService()
            self.service.start(
                cube,
                on_done=lambda result: Clock.schedule_once(
                    lambda dt: self._finish(result, run), 0),
                on_progress=lambda payload: Clock.schedule_once(
                    lambda dt, p=dict(payload): self._progress_for(run, p), 0),
            )
        except Exception as exc:
            from services.solve_service import _make_failure
            self._finish(_make_failure(exc),run)

    def _progress_for(self, run, payload):
        if self._run is run and not self._finished and not self._cancelled and self.manager.current==self.name:
            self._apply_progress(payload)

    def _apply_progress(self, payload):
        if 'search' in payload:
            self._search_metrics=dict(payload['search']);self._update_time()
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

    def _update_time(self,*_):
        from time import monotonic
        if not hasattr(self,'metrics'):return
        self.metrics.text=tr('entry.solve_elapsed',seconds=int(monotonic()-getattr(self,'_begun',monotonic())))
        data=getattr(self,'_search_metrics',{})
        if data:
            self.metrics.text+='\n'+tr('entry.search_metrics',nodes=data['expanded'],depth=data['bound'],seconds=int(data['seconds']))
            if data.get('resumed'):self.metrics.text+=' · '+tr('entry.search_resumed')

    def _finish(self, result, run):
        if self._run is not run or self._finished or self.manager.current!=self.name:
            return
        self._finished = True
        if getattr(self,'_time_event',None):self._time_event.cancel();self._time_event=None
        self.operation.finish(run);self.cancel.disabled=True
        self._release_source()
        if self._cancelled:
            self._return_to_source('','cancelled')
        elif result.success:
            try:
                if self._success is not None:
                    self._success(result)
                else:
                    _app().solve_result = result
                    self.manager.current = "PlaybackScreen"
            except Exception as exc:
                from services.failures import classify
                self._return_to_source(str(exc),'solver',classify(exception=exc))
        else:
            self._return_to_source(result.message,'cancelled' if getattr(result,'failure_kind','')=='cancelled' else 'solver',
                                   getattr(result,'failure_category','') or None,getattr(result,'error_locations',None) or None)

    def _release_source(self):
        reservation,self._source_task=self._source_task,None
        if reservation is not None:reservation[0].entry_state.finish(reservation[1])

    def _return_to_source(self,message,kind,category=None,locations=None):
        source=self.manager.get_screen(self._source)
        if hasattr(source,'entry_queue_notice'):source.entry_queue_notice(message,kind,category,locations)
        self.manager.current=self._source

    def on_cancel(self):
        if self._finished or self._cancelled:
            return
        self._cancelled = True
        self._pending = None
        self._run = None
        self.service.cancel()
        self.operation.cancel();self._release_source()
        if hasattr(self,'cancel'):self.cancel.disabled=True
        # Discard late callbacks even for solvers that cannot stop immediately.
        self._finished = True
        self._return_to_source('','cancelled')

    def back(self):
        self.on_cancel()

    def on_pre_leave(self,*_):
        self._invalidate()

    def on_leave(self):
        self._invalidate()

    def _invalidate(self):
        if getattr(self,'_time_event',None):self._time_event.cancel();self._time_event=None
        self.service.cancel()
        self._run = None
        self._finished = True
        self._success = None
        self._pending=None;self._cancelled=True
        self.operation.cancel();self._release_source()
        if hasattr(self,'cancel'):self.cancel.disabled=True


def _app():
    from kivy.app import App
    return App.get_running_app()
