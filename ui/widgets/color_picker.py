"""颜色选择器：六个颜色块，当前选中高亮。

色块用 Label + 自绘 canvas（魔方色圆角矩形 + 选中描边），避免被全局
<Button> 规则的主题背景矩形覆盖而显示成主题色（深蓝/浅咖）。
"""

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.properties import StringProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

from app.constants import COLOR_INFO, COLOR_ORDER
from cube.colors import is_valid_color
from ui.widgets import metrics as m


class ColorSelector(GridLayout):
    """当前颜色 current_color，点击回调。"""

    current_color = StringProperty("W")
    # 选中色块四周的描边粗细
    RING_WIDTH = 2.0
    CHIP_RADIUS = 10

    def __init__(self, **kwargs):
        two_rows = kwargs.pop("two_rows", False)
        self._two_rows = bool(two_rows)
        super().__init__(cols=3 if two_rows else 6, **kwargs)
        self._buttons = {}
        self.update_metrics()
        self._build()

    def update_metrics(self):
        layout = m.input_grid_metrics(
            2 if self._two_rows else 1,
            column_gap=16 if self._two_rows else 8,
            row_gap=10 if self._two_rows else 6)
        self.spacing = layout["spacing"]
        self.padding = layout["padding"]
        if self.size_hint_y is None:
            self.height = layout["height"]
        for button in self._buttons.values():
            button._ring_width = m.h(self.RING_WIDTH)
            self._update_geom(button)

    def _build(self):
        for col in COLOR_ORDER:
            name, rgba = COLOR_INFO[col]
            b = Label(text=col, font_size="16sp", halign="center", valign="middle")
            # 浅色底（白/黄）用黑色文字，深色底用白色文字，保证对比鲜明
            b.color = self._text_color(rgba)
            # 魔方色背景圆角矩形（canvas.before，不受全局 <Button> 主题矩形影响）
            with b.canvas.before:
                b._fill_ctx = Color(*rgba)
                b._fill = RoundedRectangle(pos=b.pos, size=b.size,
                                           radius=[self.CHIP_RADIUS] * 4)
            # A quiet edge keeps every swatch visually aligned with the controls.
            b._border_color = self._contrast(rgba)
            b._border_ctx = Color(*(*b._border_color[:3], 0.28))
            b._border = Line(width=0.75, rounded_rectangle=(0, 0, 0, 0, self.CHIP_RADIUS))
            # The selected outline stays inside the chip, so it cannot overlap nearby taps.
            b._ring_color = self._contrast(rgba)
            b._ring_width = m.h(self.RING_WIDTH)
            b._ring_ctx = Color(*(*b._ring_color[:3], 0.0))
            b._ring = Line(width=b._ring_width,
                           rounded_rectangle=(0, 0, 0, 0, self.CHIP_RADIUS - 2))
            b.canvas.after.add(b._border_ctx)
            b.canvas.after.add(b._border)
            b.canvas.after.add(b._ring_ctx)
            b.canvas.after.add(b._ring)
            b.bind(pos=self._update_geom, size=self._update_geom)
            b.bind(on_touch_down=lambda inst, touch, c=col: self._touch(inst, touch, c))
            self.add_widget(b)
            self._buttons[col] = b
        self._sync()

    @staticmethod
    def _contrast(rgba):
        """Use a visible selection ring on both light and dark swatches."""
        lum = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
        return (0.04, 0.08, 0.12, 1.0) if lum > 0.55 else (1.0, 1.0, 1.0, 1.0)

    @staticmethod
    def _text_color(rgba):
        """浅色底用黑色文字，深色底用白色文字。"""
        lum = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
        return (0.0, 0.0, 0.0, 1.0) if lum > 0.55 else (1.0, 1.0, 1.0, 1.0)

    def _touch(self, inst, touch, col):
        if inst.collide_point(*touch.pos):
            self.select(col)
            return True
        return False

    def _update_geom(self, b, *args):
        b._fill.pos = b.pos
        b._fill.size = b.size
        border_inset = 0.75
        b._border.rounded_rectangle = (
            b.x + border_inset, b.y + border_inset,
            max(0, b.width - border_inset * 2),
            max(0, b.height - border_inset * 2), self.CHIP_RADIUS)
        inset = b._ring_width + 1
        b._ring.rounded_rectangle = (
            b.x + inset, b.y + inset,
            max(0, b.width - inset * 2),
            max(0, b.height - inset * 2), max(2, self.CHIP_RADIUS - inset))

    def select(self, col):
        self.current_color = col
        self._sync()
        self.dispatch("on_select", col)

    def _sync(self):
        for col, b in self._buttons.items():
            rgba = COLOR_INFO[col][1]
            # 保持原底色，叠加高对比描边
            b._fill_ctx.rgba = rgba
            if col == self.current_color:
                b._ring_ctx.rgba = (*b._ring_color[:3], 1.0)
                self._update_geom(b)
            else:
                b._ring_ctx.rgba = (*b._ring_color[:3], 0.0)

    # --- events ---
    __events__ = ("on_select",)

    def on_select(self, col):
        pass
