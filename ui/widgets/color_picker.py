"""颜色选择器：六个颜色按钮，当前选中高亮。"""

from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

from app.constants import COLOR_INFO, COLOR_ORDER
from cube.colors import is_valid_color


class ColorSelector(BoxLayout):
    """当前颜色 current_color，点击回调。"""

    current_color = StringProperty("W")

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", spacing=6, **kwargs)
        self._buttons = {}
        self._build()

    def _build(self):
        for col in COLOR_ORDER:
            name, rgba = COLOR_INFO[col]
            b = Button(text=col, font_size="16sp")
            b.background_color = rgba
            b.bind(on_release=lambda b, c=col: self.select(c))
            self.add_widget(b)
            self._buttons[col] = b
        self._sync()

    def select(self, col):
        self.current_color = col
        self._sync()
        self.dispatch("on_select", col)

    def _sync(self):
        for col, b in self._buttons.items():
            if col == self.current_color:
                b.background_color = [c * 1.2 for c in COLOR_INFO[col][1][:3]] + [1.0]
            else:
                b.background_color = COLOR_INFO[col][1]

    # --- events ---
    __events__ = ("on_select",)

    def on_select(self, col):
        pass
