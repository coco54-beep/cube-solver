"""「使用说明」弹窗（自定义主题化模态框）。

从首页移到设置页；文本取自 app.i18n。
"""


def _autofit(lbl, pad=1):
    """让 Label 随文本宽度换行并自动增高，杜绝长文本溢出/重叠。"""
    lbl.size_hint_y = None
    lbl.bind(width=lambda w, s: setattr(w, "text_size", (s, None)) if s else None)

    def _h(w, tex):
        if tex[0]:
            w.height = tex[1] + pad

    lbl.bind(texture_size=_h)


_HELP_KEYS = ("select", "input", "solve", "playback",
              "demo", "theme", "notation", "algo")


def _help_sections():
    from app.i18n import tr
    return [(tr(f"help.{k}.title"), tr(f"help.{k}.body")) for k in _HELP_KEYS]


def _app():
    from kivy.app import App
    return App.get_running_app()


def show_help():
    """显示「使用说明」模态框（遮罩 + 居中面板，浅/深主题均清晰）。"""
    from app.i18n import tr
    from ui.screens.input_screen import PrimaryButton
    from ui.widgets import fx
    from kivy.uix.label import Label
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.anchorlayout import AnchorLayout
    from kivy.uix.scrollview import ScrollView
    from kivy.core.window import Window
    from kivy.graphics import Color, RoundedRectangle, Line, Rectangle
    from kivy.graphics.instructions import InstructionGroup

    theme = _app().theme
    scroll = ScrollView()

    # 遮罩层：半透明黑，铺满窗口；点击面板外关闭
    overlay = FloatLayout()

    def draw_overlay(*_):
        overlay.canvas.before.clear()
        overlay.canvas.before.add(Color(0, 0, 0, 0.45))
        overlay.canvas.before.add(Rectangle(pos=overlay.pos, size=overlay.size))

    overlay.bind(pos=draw_overlay, size=draw_overlay)
    draw_overlay()

    # 居中面板
    holder = AnchorLayout(anchor_x="center", anchor_y="center")
    holder.size_hint = (1, 1)
    panel = BoxLayout(orientation="vertical", spacing=0, size_hint=(None, None))
    panel.width = min(760, Window.width * 0.9)
    panel.height = min(560, Window.height * 0.88)
    panel._bg = InstructionGroup()
    panel.canvas.before.add(panel._bg)

    def draw_panel(*_):
        panel._bg.clear()
        t = _app().theme
        for inst in fx.soft_shadow(panel.pos, panel.size, 20, t.card_shadow,
                                   layers=2, spread=3.0, blur=8.0):
            panel._bg.add(inst)
        panel._bg.add(Color(*t.surface))
        panel._bg.add(RoundedRectangle(pos=panel.pos, size=panel.size, radius=[20] * 4))
        panel._bg.add(Color(*t.card_border))
        panel._bg.add(Line(width=1.3, rounded_rectangle=(
            panel.x + 0.6, panel.y + 0.6,
            panel.width - 1.2, panel.height - 1.2, 20)))

    panel.bind(pos=draw_panel, size=draw_panel)
    draw_panel()

    # 标题栏：标题 + 强调色横条
    header = BoxLayout(orientation="vertical", size_hint_y=None,
                       height=62, padding=[22, 14, 22, 6])
    t = Label(text=tr("help.title"), font_size="22sp", bold=True, halign="left",
              valign="middle", color=theme.text, size_hint_y=1)
    header.add_widget(t)

    bar = BoxLayout(size_hint_y=None, height=4)
    bar._bg = InstructionGroup()
    bar.canvas.before.add(bar._bg)

    def draw_bar(*_):
        bar._bg.clear()
        th = _app().theme
        bar._bg.add(Color(*th.accent))
        bar._bg.add(Rectangle(pos=bar.pos, size=bar.size))

    bar.bind(pos=draw_bar, size=draw_bar)
    draw_bar()
    header.add_widget(bar)
    panel.add_widget(header)

    # 正文卡片（滚动）
    inner = BoxLayout(orientation="vertical", spacing=6,
                      size_hint_y=None, padding=[22, 8, 22, 8])
    inner.bind(minimum_height=inner.setter("height"))
    for sec_title, body in _help_sections():
        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         spacing=2, padding=[14, 10, 14, 10])
        ct = Label(text=sec_title, font_size="18sp", bold=True, halign="left",
                   valign="middle", color=theme.text)
        cb = Label(text=body, font_size="15sp", halign="left", valign="top",
                   color=theme.text)
        _autofit(ct, pad=6)
        _autofit(cb, pad=6)
        card.add_widget(ct)
        card.add_widget(cb)
        card.bind(minimum_height=card.setter("height"))
        card._bg = InstructionGroup()
        card.canvas.before.add(card._bg)

        def draw_card(card=card):
            card._bg.clear()
            th = _app().theme
            card._bg.add(Color(*th.surface_hi))
            card._bg.add(RoundedRectangle(pos=card.pos, size=card.size,
                                          radius=[12] * 4))
            card._bg.add(Color(*th.card_border))
            card._bg.add(Line(width=1.0, rounded_rectangle=(
                card.x + 0.5, card.y + 0.5,
                card.width - 1.0, card.height - 1.0, 12)))

        card._bgedraw = draw_card
        card.bind(pos=lambda *a, c=card: c._bgedraw(),
                  size=lambda *a, c=card: c._bgedraw())
        draw_card()
        inner.add_widget(card)
    scroll.add_widget(inner)
    panel.add_widget(scroll)

    # 底部：关闭按钮
    foot = BoxLayout(size_hint_y=None, height=62, padding=[22, 10, 22, 14])
    close = PrimaryButton(text=tr("help.close"), font_size="17sp")
    foot.add_widget(close)
    panel.add_widget(foot)

    holder.add_widget(panel)
    overlay.add_widget(holder)
    Window.add_widget(overlay)

    def dismiss(*_):
        if overlay.parent is not None:
            Window.remove_widget(overlay)

    close.bind(on_release=dismiss)

    def overlay_touch(inst, touch):
        if not panel.collide_point(*touch.pos):
            dismiss()
            return True
        return False

    overlay.bind(on_touch_down=overlay_touch)
