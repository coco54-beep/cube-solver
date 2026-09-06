"""颜色选择器：六个颜色块，当前选中高亮。

色块用 Label + 自绘 canvas（魔方色圆角矩形 + 选中描边），避免被全局
<Button> 规则的主题背景矩形覆盖而显示成主题色（深蓝/浅咖）。
"""

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.constants import COLOR_INFO, COLOR_ORDER
from cube.colors import is_valid_color


class ColorSelector(BoxLayout):
    """当前颜色 current_color，点击回调。"""

    current_color = StringProperty("W")
    # 选中色块四周的描边粗细
    RING_WIDTH = 3.0

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", spacing=6, **kwargs)
        self._buttons = {}
        self._build()

    def _build(self):
        for col in COLOR_ORDER:
            name, rgba = COLOR_INFO[col]
            b = Label(text=col, font_size="16sp", halign="center", valign="middle")
            # 浅色底（白/黄）用黑色文字，深色底用白色文字，保证对比鲜明
            b.color = self._text_color(rgba)
            # 魔方色背景圆角矩形（canvas.before，不受全局 <Button> 主题矩形影响）
            with b.canvas.before:
                b._fill_ctx = Color(*rgba)
                b._fill = RoundedRectangle(pos=b.pos, size=b.size, radius=[8, 8, 8, 8])
            # 选中描边（高对比颜色），初始隐藏
            b._ring_color = self._contrast(rgba)
            b._ring_ctx = Color(*(*b._ring_color[:3], 0.0))
            b._ring = Line(width=self.RING_WIDTH, rectangle=(0, 0, 0, 0))
            b.canvas.after.add(b._ring_ctx)
            b.canvas.after.add(b._ring)
            b.bind(pos=self._update_geom, size=self._update_geom)
            b.bind(on_touch_down=lambda inst, touch, c=col: self._touch(inst, touch, c))
            self.add_widget(b)
            self._buttons[col] = b
        self._sync()

    @staticmethod
    def _contrast(rgba):
        """统一使用白色描边。"""
        return (1.0, 1.0, 1.0, 1.0)

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
        w = self.RING_WIDTH * 2
        b._ring.rectangle = (b.x - w, b.y - w, b.width + w * 2, b.height + w * 2)

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
