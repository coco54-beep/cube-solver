"""首页：选择 3 阶 / 4 阶、使用说明、版本号（美观启动页式）。"""

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.clock import Clock

from app.config import Config
from app.theme import AUTO, LIGHT, DARK


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=12, padding=[24, 24, 24, 14])

        # ---- 标题区（顶部）----
        head = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=8)
        self.title = Label(text=Config.app_name, font_size="34sp", bold=True,
                           halign="center", valign="middle", size_hint_y=None, height=90)
        self.subtitle = Label(text="2 阶 / 3 阶 / 4 阶 / 5 阶魔方 · 智能还原", font_size="15sp",
                              color=_app().theme.text_muted, halign="center",
                              valign="middle", size_hint_y=None, height=42)
        head.add_widget(self.title)
        head.add_widget(self.subtitle)
        root.add_widget(head)

        # 弹性空白：让主选择区在竖直方向居中
        root.add_widget(BoxLayout(size_hint_y=1))

        # ---- 主选择区：2 阶 / 3 阶 / 4 阶（大卡片按钮）----
        from kivy.uix.gridlayout import GridLayout
        self.cards = GridLayout(cols=4, spacing=20, size_hint=(1.0, None),
                                padding=0, height=self._card_height())
        b2 = self._card("2", "2 阶魔方", "还原 Pocket Cube", onClick=lambda *a: self.pick(2))
        b3 = self._card("3", "3 阶魔方", "还原 Rubik's Cube", onClick=lambda *a: self.pick(3))
        b4 = self._card("4", "4 阶魔方", "还原 Rubik's Revenge", onClick=lambda *a: self.pick(4))
        b5 = self._card("5", "5 阶魔方", "还原 Professor's Cube", onClick=lambda *a: self.pick(5))
        for b in (b2, b3, b4, b5):
            self.cards.add_widget(b)
        root.add_widget(self.cards)
        # 横屏 1×4，竖屏 2×2；监听窗口尺寸变化重排。
        from kivy.core.window import Window
        self._last_win_size = None
        Window.bind(size=self._relayout)
        Clock.schedule_once(self._relayout, 0.1)
        # 兜底轮询：Kivy 的 Window.size 事件在部分平台（尤其 Android 转屏、
        # 或以代码方式改尺寸）不触发，主动周期性比对，尺寸变了才重排。
        Clock.schedule_interval(self._poll_layout, 0.2)

        # ---- 操作区 ----
        actions = BoxLayout(orientation="horizontal", spacing=10,
                            size_hint=(1.0, None), height=52)
        help_btn = Button(text="使用说明", font_size="17sp")
        help_btn.bind(on_release=lambda *a: self.show_help())
        self.theme_btn = Button(text="主题：自动", font_size="15sp")
        self.theme_btn.bind(on_release=lambda *a: self.cycle_theme())
        actions.add_widget(help_btn)
        actions.add_widget(self.theme_btn)
        root.add_widget(actions)
        self._update_theme_btn()

        # 弹性空白
        root.add_widget(BoxLayout(size_hint_y=1))

        # ---- 底部版本 ----
        bottom = AnchorLayout(size_hint_y=None, height=40)
        self._ver_label = Label(text=f"版本 {Config.app_version}", font_size="13sp",
                                color=_app().theme.text_faint, halign="center", valign="middle")
        bottom.add_widget(self._ver_label)
        root.add_widget(bottom)

        self.add_widget(root)

    def _card_height(self, h=None):
        """卡片区高度，随屏幕尺寸微调（基准高屏 240，小屏略降）。"""
        from kivy.core.window import Window
        h = h if h is not None else (Window.height if Window.height else 800)
        return int(max(180, min(240, h * 0.30)))

    def _card_size(self, w=None):
        """方块卡片尺寸：竖屏 2×2 时按列宽近似正方形。"""
        from kivy.core.window import Window
        w = w if w is not None else (Window.width if Window.width else 420)
        sp = self.cards.spacing
        gap = sp[0] if isinstance(sp, (list, tuple)) else sp
        return int((w - 48 - gap) / 2)

    def _relayout(self, *args):
        from kivy.core.window import Window
        self._apply_layout(Window.width, Window.height)

    def _poll_layout(self, _dt):
        """兜底：周期性检查窗口尺寸，变了才重排（避免依赖不稳定的 size 事件）。"""
        from kivy.core.window import Window
        cur = (Window.width, Window.height)
        if cur != self._last_win_size:
            self._apply_layout(*cur)

    def _apply_layout(self, w, h):
        """横屏：4 列 1 行（1×4）；竖屏：2 列 2 行（2×2）。"""
        self._last_win_size = (w, h)
        if w > h:
            self.cards.cols = 4
            self.cards.height = self._card_height(h)
        else:
            self.cards.cols = 2
            side = self._card_size(w)
            self.cards.height = side * 2 + self.cards.spacing[0]

    def _card(self, big, title, desc, onClick):
        """创建一个卡片式按钮（大字标题 + 描述）。"""
        from kivy.graphics import Color, RoundedRectangle
        theme = _app().theme
        card = BoxLayout(orientation="vertical", spacing=2, padding=10)
        card.bind(on_touch_down=lambda instance, touch, c=card: self._on_card_touch(c, touch))
        with card.canvas.before:
            fill = Color(*theme.surface)
            rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[16, 16, 16, 16])
        card.bind(pos=lambda *a: setattr(rect, "pos", card.pos),
                  size=lambda *a: setattr(rect, "size", card.size))
        # 用 size_hint 比例占满卡片，避免固定高度导致文字重叠
        big_label = Label(text=big, font_size="46sp", bold=True, halign="center",
                          valign="middle", color=theme.text, size_hint_y=0.52)
        title_label = Label(text=title, font_size="19sp", bold=True, halign="center",
                            valign="middle", color=theme.text, size_hint_y=0.26)
        desc_label = Label(text=desc, font_size="13sp", halign="center",
                           valign="middle", color=theme.text_muted, size_hint_y=0.22)
        card.add_widget(big_label)
        card.add_widget(title_label)
        card.add_widget(desc_label)
        card._on_click = onClick
        card._fill_rgba = fill
        card._labels = (big_label, title_label, desc_label)
        return card

    def _update_theme_btn(self):
        labels = {AUTO: "主题：自动", LIGHT: "主题：浅色", DARK: "主题：深色"}
        self.theme_btn.text = labels.get(_app().theme_mode, "主题：自动")

    def cycle_theme(self):
        app = _app()
        order = (AUTO, LIGHT, DARK)
        idx = order.index(app.theme_mode)
        app.set_theme_mode(order[(idx + 1) % len(order)])
        self.refresh_theme()

    def refresh_theme(self):
        """主题切换后刷新 Python 端硬编码的颜色。"""
        theme = _app().theme
        self.subtitle.color = theme.text_muted
        self._ver_label.color = theme.text_faint
        self._update_theme_btn()
        cards = getattr(self, "cards", None)
        if cards:
            for card in cards.children:
                try:
                    card._fill_rgba.rgba = theme.surface
                    big, title, desc = card._labels
                    big.color = theme.text
                    title.color = theme.text
                    desc.color = theme.text_muted
                except Exception:
                    pass

    def _on_card_touch(self, card, touch):
        if card.collide_point(*touch.pos):
            if getattr(card, "_on_click", None):
                card._on_click()
            return True
        return False

    def pick(self, n: int):
        app = _app()
        app.new_cube(n)
        self.manager.current = "InputScreen"

    def show_help(self):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        body = BoxLayout(orientation="vertical", spacing=8, padding=12)
        sections = [
            ("录入", "点击对应阶进入录入页，逐格输入每个面的颜色。\n"
                     "可用「随机」快速加载一个打乱布局测试破解。"),
            ("求解", "录入完成后点「开始求解」，程序计算还原步骤。"),
            ("回放", "用 3D 视图演示还原：拖动旋转视角，滚轮/双指缩放；\n"
                     "支持上一步 / 下一步 / 自动播放 / 跳结尾。"),
        ]
        for title, text in sections:
            t = Label(text=title, font_size="17sp", bold=True,
                      halign="left", valign="middle", size_hint_y=None, height=30)
            l = Label(text=text, font_size="15sp", color=(0.85, 0.88, 0.93, 1),
                      halign="left", valign="top", size_hint_y=None, height=62)
            body.add_widget(t)
            body.add_widget(l)
        popup = Popup(title="使用说明", content=body, size_hint=(0.9, 0.7))
        # 文字换行：绑定 text_size 到各自尺寸
        for w in body.children:
            if isinstance(w, Label):
                w.bind(size=lambda ins, s: setattr(ins, "text_size", s))
        popup.open()


def _app():
    from kivy.app import App
    return App.get_running_app()
