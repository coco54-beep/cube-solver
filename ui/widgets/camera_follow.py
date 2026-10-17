"""Shared camera-follow slider for solution playback, turns and settings."""
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.slider import Slider

from app.i18n import tr
from renderer.camera_follow import FOLLOW_SETTINGS, MIN_RATE, MAX_RATE, bind_camera_settings
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets.buttons import UIButton


class CameraFollowControl(ResponsiveBoxLayout):
    def __init__(self,show_lock=True, **kwargs):
        super().__init__(height_px=44, gap_px=6, **kwargs)
        self.label = Label(font_size='13sp', size_hint_x=.24,
                           halign='center', valign='middle')
        self.label.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        self.slider = Slider(min=0, max=MAX_RATE, step=MIN_RATE,
                             value=FOLLOW_SETTINGS.rate, size_hint_x=.76)
        self.lock_button=None
        if show_lock:
            self.lock_button=UIButton(icon_name='lock',size_hint_x=.12)
            self.lock_button.bind(on_release=lambda *_:setattr(FOLLOW_SETTINGS,'locked',not FOLLOW_SETTINGS.locked))
            self.add_widget(self.lock_button)
        self.add_widget(self.label)
        self.add_widget(self.slider)
        self.slider.bind(value=self._changed)
        FOLLOW_SETTINGS.bind(rate=self._sync)
        FOLLOW_SETTINGS.bind(locked=self._lock_changed)
        app = App.get_running_app()
        if app is not None:
            self.label.color = app.theme.text
            app.theme.bind(text=self._theme_changed)
        self.retranslate()

    def bind_view(self,view,on_change=None):
        bind_camera_settings(view,on_change)

    def _lock_changed(self,*_):
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
        if self.lock_button is not None:
            self.lock_button.icon_name='lock' if FOLLOW_SETTINGS.locked else 'unlock'
            self.lock_button.active=FOLLOW_SETTINGS.locked
        value = FOLLOW_SETTINGS.rate
        status = tr('camera.follow_off') if value <= 0 else f'{round(value)}°/s'
        self.label.text = tr('camera.follow') + '\n' + status


def follow_panel(panel,view=None,on_change=None,show_lock=True):
    """Keep camera controls usable while the screen disables turn controls."""
    panel.size_hint_y = None
    panel.bind(minimum_height=panel.setter('height'))
    panel.height = panel.minimum_height
    wrapper = ResponsiveBoxLayout(orientation='vertical', gap_px=8,
                                  size_hint_y=None)
    control = CameraFollowControl(show_lock=show_lock)
    if view is not None:
        control.bind_view(view,on_change)
    wrapper.add_widget(panel)
    wrapper.add_widget(control)
    return wrapper, control
