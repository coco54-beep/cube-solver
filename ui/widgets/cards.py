"""首页风格的卡片组件：柔和投影 + 圆角底 + 描边 + 大号强调数字。

首页与异形目录页共用，保证两处视觉一致。
"""

from kivy.app import App
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.graphics.instructions import InstructionGroup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from ui.widgets import fx
from ui.widgets import metrics as m


def _theme():
    return App.get_running_app().theme


class HomeCard(BoxLayout):
    """大号强调文字 + 标题的卡片按钮，绘制风格与首页一致。"""

    def __init__(self, big, title, on_click=None, **kwargs):
        super().__init__(orientation="vertical", spacing=2, padding=10, **kwargs)
        self._pressed = False
        self._on_click = on_click
        self._bg = InstructionGroup()
        self.canvas.before.add(self._bg)
        self.bind(pos=lambda *a: self._draw(), size=lambda *a: self._draw())
        theme = _theme()
        self._big = Label(text=big, font_size="46sp", bold=True, halign="center",
                          valign="middle", color=theme.text, size_hint_y=0.62)
        self._title = Label(text=title, font_size="18sp", bold=True, halign="center",
                            valign="middle", color=theme.text, size_hint_y=0.38)
        self._title.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        self.add_widget(self._big)
        self.add_widget(self._title)
        self._labels = (self._big, self._title)
        self.bind(size=self._restyle)
        self._draw()

    def set_text(self, big, title):
        self._big.text = big
        self._title.text = title

    def set_title(self, title):
        self._title.text = title

    def _restyle(self, *_args):
        height = self.height / max(1e-6, _scale_factor())
        self._big.font_size = m.font(max(22, min(46, height * 0.32)))
        self._title.font_size = m.font(max(11, min(18, height * 0.13)))
        self.padding = m.h(max(4, min(10, height * 0.055)))

    def _draw(self):
        theme = _theme()
        g = self._bg
        g.clear()
        for inst in fx.soft_shadow(self.pos, self.size, 18, theme.card_shadow,
                                   layers=2, spread=2.0, blur=3.0):
            g.add(inst)
        base = theme.surface_hi if self._pressed else theme.surface
        g.add(Color(*base))
        g.add(RoundedRectangle(pos=self.pos, size=self.size, radius=[14] * 4))
        g.add(Color(*theme.card_border))
        g.add(Line(width=0.9, rounded_rectangle=(
            self.x + 0.7, self.y + 0.7, self.width - 1.4, self.height - 1.4, 14)))

    def refresh_theme(self):
        theme = _theme()
        self._big.color = theme.text
        self._title.color = theme.text
        self._draw()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._pressed = True
            self._draw()
            return True
        return False

    def on_touch_up(self, touch):
        if self._pressed:
            was = self.collide_point(*touch.pos)
            self._pressed = False
            self._draw()
            if was and self._on_click is not None:
                self._on_click()
            return True
        return False


def _scale_factor():
    from ui.widgets import metrics as m
    return m.scale_factor()
