"""Control layouts that follow the native window's final resolution."""

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout

from ui.widgets import metrics as m


class ResponsiveBoxLayout(BoxLayout):
    def __init__(self, height_px=None, gap_px=None, padding_px=None, **kwargs):
        self._height_px = height_px
        self._gap_px = gap_px
        self._padding_px = padding_px
        if height_px is not None:
            kwargs["size_hint_y"] = None
        super().__init__(**kwargs)
        self._resize_trigger = Clock.create_trigger(self._sync_metrics, 0)
        Window.bind(size=self._schedule_metrics, on_resize=self._schedule_metrics)
        self._sync_metrics()

    def _schedule_metrics(self, *_args):
        self._resize_trigger()

    def _sync_metrics(self, *_args):
        if self._height_px is not None:
            self.height = m.h(self._height_px)
        if self._gap_px is not None:
            self.spacing = m.h(self._gap_px)
        if self._padding_px is not None:
            padding = self._padding_px
            if isinstance(padding, (list, tuple)):
                self.padding = [m.h(value) for value in padding]
            else:
                self.padding = m.h(padding)
