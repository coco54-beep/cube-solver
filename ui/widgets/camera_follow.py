"""Shared camera-follow slider for solution playback, turns and settings."""
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.slider import Slider

from app.i18n import tr
from renderer.camera_follow import FOLLOW_SETTINGS, MIN_RATE, MAX_RATE
from ui.widgets.layouts import ResponsiveBoxLayout


class CameraFollowControl(ResponsiveBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(height_px=44, gap_px=6, **kwargs)
        self.label = Label(font_size='13sp', size_hint_x=.24,
                           halign='center', valign='middle')
        self.label.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        self.slider = Slider(min=0, max=MAX_RATE, step=MIN_RATE,
                             value=FOLLOW_SETTINGS.rate, size_hint_x=.76)
        self.add_widget(self.label)
        self.add_widget(self.slider)
        self.slider.bind(value=self._changed)
        FOLLOW_SETTINGS.bind(rate=self._sync)
        app = App.get_running_app()
        if app is not None:
            self.label.color = app.theme.text
            app.theme.bind(text=self._theme_changed)
        self.retranslate()

    def _changed(self, _slider, value):
        FOLLOW_SETTINGS.rate = value

    def _sync(self, _settings, value):
        # Assign only when needed so syncing another page never writes again.
        if self.slider.value != value:
            self.slider.value = value
        self.retranslate()

    def _theme_changed(self, _theme, color):
        self.label.color = color

    def retranslate(self):
        value = FOLLOW_SETTINGS.rate
        status = tr('camera.follow_off') if value <= 0 else f'{round(value)}°/s'
        self.label.text = tr('camera.follow') + '\n' + status


def follow_panel(panel):
    """Keep the slider usable while a screen disables its other turn controls."""
    panel.size_hint_y = None
    panel.bind(minimum_height=panel.setter('height'))
    panel.height = panel.minimum_height
    wrapper = ResponsiveBoxLayout(orientation='vertical', gap_px=8,
                                  size_hint_y=None)
    control = CameraFollowControl()
    wrapper.add_widget(panel)
    wrapper.add_widget(control)
    return wrapper, control
