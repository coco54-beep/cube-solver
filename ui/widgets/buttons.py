from kivy.app import App
from kivy.graphics import BorderImage, Color, Line, RoundedRectangle
from kivy.graphics.instructions import InstructionGroup
from kivy.uix.button import Button

from ui.widgets import fx


class UIButton(Button):
    """圆角渐变按钮基类。

    处理两件事：
    1. 移除 Kivy 默认在自身 canvas 里画的方形背景 BorderImage，让它不覆盖
       canvas.before 中的圆角矩形。
    2. 在 canvas.before 里绘制：柔和投影 + 垂直渐变填充 + 顶部高光 + 描边，
       并在 state（normal/pressed）、pos/size 与主题切换时刷新，形成精致按键观感。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for c in list(self.canvas.children):
            if isinstance(c, BorderImage):
                self.canvas.remove(c)
        # 背景指令组，整体放在 canvas.before 中，便于整体重建。
        self._bg = InstructionGroup()
        self.canvas.before.add(self._bg)
        self.bind(pos=self._rebuild, size=self._rebuild)
        self.bind(state=lambda *a: self._rebuild())
        app = App.get_running_app()
        if app is not None:
            app.theme.bind(on_palette=lambda *a: self._rebuild())
        self._rebuild()

    # ---- 配色 ----
    def _button_color(self):
        theme = self._theme()
        if theme is None:
            return self.background_color
        if type(self).__name__ == "PrimaryButton":
            return theme.primary
        if type(self).__name__ == "DangerButton":
            return theme.danger
        return theme.button

    def _pressed_color(self):
        theme = self._theme()
        if theme is None:
            return self.background_color
        if type(self).__name__ == "PrimaryButton":
            return theme.primary_pressed
        if type(self).__name__ == "DangerButton":
            return theme.danger_pressed
        return theme.button_pressed

    def _theme(self):
        app = App.get_running_app()
        return app.theme if app is not None else None

    # ---- 绘制 ----
    def _draw(self, ctx):
        ctx.clear()
        theme = self._theme()
        pressed = self.state != "normal"
        fill = self._pressed_color() if pressed else self._button_color()

        # 柔和投影
        shadow = theme.card_shadow if theme is not None else (0, 0, 0, 0.35)
        for inst in fx.soft_shadow(self.pos, self.size, 12, shadow,
                                   layers=3, spread=3.0, blur=5.0):
            ctx.add(inst)

        # 圆角实心底
        ctx.add(Color(*fill))
        ctx.add(RoundedRectangle(pos=self.pos, size=self.size, radius=[12] * 4))

        # 描边
        border = theme.border if theme is not None else (0.5, 0.5, 0.5, 1)
        border_ctx = Color(*border)
        line = Line(width=1.2,
                    rounded_rectangle=(self.x + 0.6, self.y + 0.6,
                                       self.width - 1.2, self.height - 1.2, 12))
        ctx.add(border_ctx)
        ctx.add(line)

    def _rebuild(self, *args):
        self._draw(self._bg)


class PrimaryButton(UIButton):
    """主操作按钮（绿色主题，见 app.kv 的 <PrimaryButton> 规则）。"""


class DangerButton(UIButton):
    """危险按钮（红色主题，见 app.kv 的 <DangerButton> 规则）。"""
