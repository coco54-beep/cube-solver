from kivy.app import App
from kivy.graphics import BorderImage, Color, Rectangle, RoundedRectangle
from kivy.graphics.instructions import InstructionGroup
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.button import Button

from ui.widgets import fx
from ui.widgets.icons import icon_image


class UIButton(Button):
    """圆角渐变按钮基类。

    处理两件事：
    1. 移除 Kivy 默认在自身 canvas 里画的方形背景 BorderImage，让它不覆盖
       canvas.before 中的圆角矩形。
    2. 在 canvas.before 里绘制：柔和投影 + 垂直渐变填充 + 顶部高光 + 描边，
       并在 state（normal/pressed）、pos/size 与主题切换时刷新，形成精致按键观感。
    """

    icon_name = StringProperty("")
    active = BooleanProperty(False)

    def __init__(self, **kwargs):
        kwargs["icon_name"] = kwargs.get("icon_name") or ""
        super().__init__(**kwargs)
        for c in list(self.canvas.children):
            if isinstance(c, BorderImage):
                self.canvas.remove(c)
        # 背景指令组，整体放在 canvas.before 中，便于整体重建。
        self._bg = InstructionGroup()
        self.canvas.before.add(self._bg)
        self.bind(pos=self._rebuild, size=self._rebuild)
        self.bind(state=lambda *a: self._rebuild())
        self.bind(disabled=lambda *a: self._rebuild())
        self.bind(icon_name=self._rebuild, active=self._rebuild)
        app = App.get_running_app()
        if app is not None:
            app.theme.bind(on_palette=lambda *a: self._rebuild())
        self._rebuild()

    # ---- 配色 ----
    def _button_color(self):
        theme = self._theme()
        if theme is None:
            return self.background_color
        if isinstance(self, PrimaryButton):
            return theme.primary
        if isinstance(self, DangerButton):
            return theme.danger
        if self.active:
            return theme.button_pressed
        return theme.button

    def _pressed_color(self):
        theme = self._theme()
        if theme is None:
            return self.background_color
        if isinstance(self, PrimaryButton):
            return theme.primary_pressed
        if isinstance(self, DangerButton):
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
        for inst in fx.soft_shadow(self.pos, self.size, 10, shadow,
                                   layers=2, spread=0.8, blur=1.5):
            ctx.add(inst)

        # 圆角实心底
        # Avoid Line(rounded_rectangle=...): its antialiased stroke can leave
        # stray pixels beyond the corners on some Android GPUs.

        # 描边
        border = (theme.accent if self.active else
                  theme.accent_dim if isinstance(self, PrimaryButton) else theme.border
                  ) if theme is not None else (0.5, 0.5, 0.5, 1)
        ctx.add(Color(*border))
        ctx.add(RoundedRectangle(pos=self.pos, size=self.size, radius=[10] * 4))

        inset = min(1.0, self.width / 2, self.height / 2)
        ctx.add(Color(*fill))
        ctx.add(RoundedRectangle(
            pos=(self.x + inset, self.y + inset),
            size=(max(0, self.width - inset * 2), max(0, self.height - inset * 2)),
            radius=[max(0, 10 - inset)] * 4,
        ))

    def _rebuild(self, *args):
        self._draw(self._bg)
        if self.icon_name:
            self._draw_icon(self._bg)

    def _draw_icon(self, ctx):
        if self.width <= 1 or self.height <= 1:
            return
        theme = self._theme()
        if theme is None:
            color = (1, 1, 1, 1)
        elif self.disabled:
            color = theme.disabled_text
        elif isinstance(self, PrimaryButton):
            color = theme.primary_text
        elif isinstance(self, DangerButton):
            color = theme.danger_text
        elif self.active:
            color = theme.accent
        else:
            color = theme.button_text

        cx, cy = self.center
        size = min(self.width, self.height) * 0.56
        img = icon_image(self.icon_name)
        if img is None:
            return
        ctx.add(Color(*color))
        ctx.add(Rectangle(texture=img.texture,
                          pos=(cx - size / 2, cy - size / 2),
                          size=(size, size)))


class PrimaryButton(UIButton):
    """主操作按钮（绿色主题，见 app.kv 的 <PrimaryButton> 规则）。"""


class DangerButton(UIButton):
    """危险按钮（红色主题，见 app.kv 的 <DangerButton> 规则）。"""


class GearButton(UIButton):
    """Settings button using the shared icon family."""

    def __init__(self, **kwargs):
        kwargs.setdefault("text", "")
        kwargs.setdefault("icon_name", "gear")
        super().__init__(**kwargs)


class ArrowButton(UIButton):
    """粗箭头按钮（上一步 / 下一步）：自绘一个加粗的 < 或 >。

    中文字体里的 < > 是细线条，和实心的播放 ▶ 不搭；这里用 canvas 画粗箭头。
    """

    def __init__(self, direction="right", **kwargs):
        kwargs.setdefault("text", "")
        kwargs.setdefault("icon_name", "prev" if direction == "left" else "next")
        self._direction = direction
        super().__init__(**kwargs)

    def _rebuild(self, *args):
        self._draw(self._bg)
        self._draw_arrow(self._bg)

    def _draw_arrow(self, ctx):
        UIButton._draw_icon(self, ctx)


class PlayPauseButton(PrimaryButton):
    """Playback control with matching play and pause icons."""

    def __init__(self, **kwargs):
        kwargs.setdefault("text", "")
        kwargs.setdefault("icon_name", "solve")
        self.playing = False
        super().__init__(**kwargs)

    def set_playing(self, playing):
        self.playing = bool(playing)
        self.icon_name = "pause" if self.playing else "solve"
