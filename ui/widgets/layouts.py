"""Control layouts that follow the native window's final resolution."""

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView

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


class AdaptiveSceneLayout(ResponsiveBoxLayout):
    """Keep the same scene and controls while switching between stacked/split UI."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("gap_px", 8)
        kwargs.setdefault("padding_px", [8, 6, 8, 8])
        super().__init__(**kwargs)
        self.body = ResponsiveBoxLayout(gap_px=16)
        self.scene = self.panel = self.panel_viewport = None
        self.portrait_fraction = None
        self._layout_trigger = Clock.create_trigger(self._adapt, 0)
        self.bind(size=lambda *_: self._layout_trigger())
        self.body.bind(size=lambda *_: self._layout_trigger())

    def set_content(self, scene, panel, portrait_fraction=None):
        self.scene, self.panel = scene, panel
        self.portrait_fraction = portrait_fraction
        if portrait_fraction is None:
            panel.size_hint_y = None
            panel.bind(minimum_height=panel.setter("height"))
            panel.height = panel.minimum_height
            viewport = ScrollView(do_scroll_x=False, bar_width=m.h(3))
            viewport.add_widget(panel)
            viewport.bind(width=lambda widget, width: setattr(panel, "width", width))
            panel.bind(height=lambda *_: self._layout_trigger())
        else:
            viewport = panel
        self.panel_viewport = viewport
        self.body.add_widget(scene)
        self.body.add_widget(viewport)
        self.add_widget(self.body)
        self._layout_trigger()

    def replace_scene(self, scene):
        self.body.remove_widget(self.scene)
        self.scene = scene
        self.body.add_widget(scene, index=1)
        self._layout_trigger()

    def _adapt(self, *_):
        if self.scene is None:
            return
        # Reconcile the final window metrics after the native resize and the
        # layout pass. This also covers screens built during a rotation.
        for widget in self.walk():
            if isinstance(widget, ResponsiveBoxLayout):
                widget._sync_metrics()
        wide = self.width > self.height * 1.1
        self.body.orientation = "horizontal" if wide else "vertical"
        if wide:
            self.scene.size_hint = (.46, 1)
            self.panel_viewport.size_hint = (.54, 1)
        else:
            self.scene.size_hint = (1, 1)
            self.panel_viewport.size_hint = (1, None)
            available = max(1, self.body.height - self.body.spacing)
            target = (available * self.portrait_fraction if self.portrait_fraction is not None
                      else min(self.panel.height, available * .62))
            self.panel_viewport.height = target
