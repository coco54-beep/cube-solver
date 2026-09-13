from kivy.app import App
from kivy.graphics import (BorderImage, Color, Ellipse, Line, Rectangle,
                           RoundedRectangle, Triangle)
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


class GearButton(UIButton):
    """齿轮图标按钮（用于「设置」）：在按钮底色上自绘一个齿轮，随主题变色。

    中文字体不含 ⚙（U+2699）等齿轮字形，故用 canvas 直接绘制（外圈齿 +
    中心孔），无需额外字体/图片资源。
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("text", "")
        super().__init__(**kwargs)

    def _rebuild(self, *args):
        # 先画按钮底色，再把齿轮叠加在同一指令组里（canvas.before 已验证可渲染）。
        self._draw(self._bg)
        self._draw_gear(self._bg)

    def _draw_gear(self, ctx):
        import math
        if self.width <= 1 or self.height <= 1:
            return
        theme = self._theme()
        icon = theme.button_text if theme is not None else (1, 1, 1, 1)
        hole = self._pressed_color() if self.state != "normal" else self._button_color()
        cx, cy = self.center
        s = min(self.width, self.height)
        r_root = s * 0.21
        r_tip = s * 0.31
        r_hole = s * 0.095
        n = 8
        a_base = math.pi / n * 0.60
        a_tip = math.pi / n * 0.30
        pts = []
        for k in range(n):
            th = 2.0 * math.pi * k / n
            pts.append((cx + math.cos(th - a_base) * r_root,
                        cy + math.sin(th - a_base) * r_root))
            pts.append((cx + math.cos(th - a_tip) * r_tip,
                        cy + math.sin(th - a_tip) * r_tip))
            pts.append((cx + math.cos(th + a_tip) * r_tip,
                        cy + math.sin(th + a_tip) * r_tip))
            pts.append((cx + math.cos(th + a_base) * r_root,
                        cy + math.sin(th + a_base) * r_root))
        verts = []
        for i in range(len(pts)):
            p = pts[i]
            q = pts[(i + 1) % len(pts)]
            verts.append((cx, cy, p[0], p[1], q[0], q[1]))
        ctx.add(Color(*icon))
        for tri in verts:
            ctx.add(Triangle(points=list(tri)))
        # 中心孔：用按钮底色挖空。
        ctx.add(Color(*hole))
        ctx.add(Ellipse(pos=(cx - r_hole, cy - r_hole),
                        size=(2 * r_hole, 2 * r_hole)))


class ArrowButton(UIButton):
    """粗箭头按钮（上一步 / 下一步）：自绘一个加粗的 < 或 >。

    中文字体里的 < > 是细线条，和实心的播放 ▶ 不搭；这里用 canvas 画粗箭头。
    """

    def __init__(self, direction="right", **kwargs):
        kwargs.setdefault("text", "")
        self._direction = direction
        super().__init__(**kwargs)

    def _rebuild(self, *args):
        self._draw(self._bg)
        self._draw_arrow(self._bg)

    def _draw_arrow(self, ctx):
        if self.width <= 1 or self.height <= 1:
            return
        theme = self._theme()
        color = theme.button_text if theme is not None else (1, 1, 1, 1)
        cx, cy = self.center
        s = min(self.width, self.height)
        hw = s * 0.11
        hh = s * 0.20
        width = max(1.8, s * 0.067)
        d = 1.0 if self._direction == "right" else -1.0
        pts = [cx - d * hw, cy + hh,
               cx + d * hw, cy,
               cx - d * hw, cy - hh]
        ctx.add(Color(*color))
        ctx.add(Line(points=pts, width=width, cap="round", joint="round"))


class PlayPauseButton(UIButton):
    """播放/暂停按钮：自绘实心三角 ▶ 或两根竖条 ▮▮（随状态与主题变化）。"""

    def __init__(self, **kwargs):
        kwargs.setdefault("text", "")
        self.playing = False
        super().__init__(**kwargs)

    def set_playing(self, playing):
        playing = bool(playing)
        if playing != self.playing:
            self.playing = playing
            self._rebuild()

    def _rebuild(self, *args):
        self._draw(self._bg)
        self._draw_icon(self._bg)

    def _draw_icon(self, ctx):
        if self.width <= 1 or self.height <= 1:
            return
        theme = self._theme()
        color = theme.button_text if theme is not None else (1, 1, 1, 1)
        cx, cy = self.center
        s = min(self.width, self.height)
        ctx.add(Color(*color))
        if self.playing:
            bw = s * 0.12
            bh = s * 0.42
            gap = s * 0.20
            for dx in (-gap / 2.0, gap / 2.0):
                ctx.add(Rectangle(pos=(cx + dx - bw / 2.0, cy - bh / 2.0),
                                  size=(bw, bh)))
        else:
            hw = s * 0.15
            hh = s * 0.21
            ctx.add(Triangle(points=[cx - hw, cy + hh,
                                     cx + hw, cy,
                                     cx - hw, cy - hh]))
