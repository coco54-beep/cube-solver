"""单个面的颜色网格（n x n），点击格子填入当前颜色。

格子带黑色边框，呈现标准魔方展开图的样式。
"""

from kivy.properties import NumericProperty, StringProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.graphics import Line, Color

from app.constants import COLOR_INFO

_BORDER = (0.05, 0.05, 0.05, 1)  # 黑色边框
_EMPTY = (0.20, 0.23, 0.30, 1)   # 空格的深蓝灰底（与白色/浅色格明显区分）


class FaceGrid(GridLayout):
    """face 面网格。face: "U"/"D"/... 用于标记。

    on_change: 每次格子的值变化后调用 (该网格无需参数，直接读 get_grid)。
    """

    face = StringProperty("U")
    size_n = NumericProperty(3)
    cell_size = NumericProperty(38)  # 每格像素尺寸
    show_labels = True  # 是否显示面标签/行列号

    def __init__(self, on_change=None, show_labels=True, **kwargs):
        super().__init__(cols=1, **kwargs)
        self.show_labels = show_labels
        self._cells = {}  # (r,c) -> Button
        self._data = {}
        self._on_change = on_change
        self.build()

    def build(self):
        self.clear_widgets()
        self._cells.clear()
        n = int(self.size_n)
        # 有标签时网格为 n+1 列（面标签 + 列号），无标签时纯 n 列
        self.cols = n + 1 if self.show_labels else n
        self.canvas.before.clear()
        cs = self.cell_size
        # 整体尺寸：显示标签则 1 列额外空间
        extra = 1 if self.show_labels else 0
        self.size_hint = (None, None)
        self.width = (n + extra) * cs
        self.height = (n + extra) * cs
        if self.show_labels:
            self.add_widget(self._label(self.face, cs))
            for c in range(n):
                self.add_widget(self._label(str(c), cs))
        for r in range(n):
            if self.show_labels:
                self.add_widget(self._label(str(r), cs))
            for c in range(n):
                b = self._make_cell(r, c, cs)
                self._cells[(r, c)] = b
                self.add_widget(b)
        # 外框 + 内部网格线画在最上层（canvas.after），避免被格子底色覆盖。
        # 使用局部坐标 (0,0)（部件原点），确保与 GridLayout 里的格子对齐。
        self.canvas.after.clear()
        with self.canvas.after:
            Color(*_BORDER)
            self._outer = Line(rectangle=(0, 0, self.width, self.height), width=3)
            self._glines = []
            grid_x0 = extra * cs
            grid_x1 = grid_x0 + n * cs
            grid_y1 = n * cs
            for i in range(n + 1):
                x = grid_x0 + i * cs
                self._glines.append(Line(points=[x, 0, x, grid_y1], width=2))
            for j in range(n + 1):
                y = j * cs
                self._glines.append(Line(points=[grid_x0, y, grid_x1, y], width=2))
        self.bind(pos=self._update_outer, size=self._update_outer)

    def _update_outer(self, *args):
        self._outer.rectangle = (0, 0, self.width, self.height)
        n = int(self.size_n)
        cs = self.cell_size
        extra = 1 if self.show_labels else 0
        grid_x0 = extra * cs
        grid_x1 = grid_x0 + n * cs
        grid_y1 = n * cs
        gi = 0
        for i in range(n + 1):
            x = grid_x0 + i * cs
            self._glines[gi].points = [x, 0, x, grid_y1]
            gi += 1
        for j in range(n + 1):
            y = j * cs
            self._glines[gi].points = [grid_x0, y, grid_x1, y]
            gi += 1

    def _make_cell(self, r, c, cs):
        b = Button(size_hint=(None, None), size=(cs - 2, cs - 2))
        b.background_normal = ""
        b.background_color = _EMPTY
        # 清除全局 <Button> 的圆角蓝底，改用背景色直接上色；
        # 网格线由 FaceGrid 在最上层统一绘制。
        b.canvas.before.clear()
        b.bind(on_release=lambda b, rr=r, cc=c: self._click_cell(rr, cc))
        return b

    def _label(self, text, cs):
        from kivy.uix.label import Label
        return Label(text=text, size_hint=(None, None),
                     size=(cs, cs), font_size="12sp")

    def _click_cell(self, r, c):
        col = self._picker_color if hasattr(self, "_picker_color") else "W"
        self._data[(r, c)] = col
        self._paint(r, c, col)
        if self._on_change is not None:
            self._on_change()

    # 兼容旧调用（外部可能直接调 on_cell）
    def on_cell(self, r, c):
        self._click_cell(r, c)

    def _paint(self, r, c, col):
        b = self._cells[(r, c)]
        rgba = COLOR_INFO.get(col, (1, 1, 1, 1))[1]
        b.background_color = rgba
        b.text = col

    def set_color(self, col):
        self._picker_color = col

    def get_grid(self):
        """返回当前面的 n x n 颜色矩阵。"""
        n = int(self.size_n)
        return [[self._data.get((r, c), "") for c in range(n)] for r in range(n)]

    def set_grid(self, grid):
        """设置整面颜色。"""
        n = int(self.size_n)
        for r in range(n):
            for c in range(n):
                col = grid[r][c] if r < len(grid) and c < len(grid[r]) else ""
                self._data[(r, c)] = col
                if col:
                    self._paint(r, c, col)
                else:
                    b = self._cells[(r, c)]
                    b.background_color = _EMPTY
                    b.text = ""
