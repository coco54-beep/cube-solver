"""首页：选择 3 阶 / 4 阶、使用说明、版本号（美观启动页式）。"""

from ui.widgets.buttons import GearButton
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.clock import Clock

from app.config import Config
from app.i18n import tr


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=12, padding=[24, 14, 24, 14])

        # ---- 顶栏：设置齿轮（右上角）----
        topbar = BoxLayout(orientation="horizontal", size_hint_y=None, height=52)
        topbar.add_widget(BoxLayout(size_hint_x=1))
        self.settings_btn = GearButton(size_hint_x=None, width=52)
        self.settings_btn.bind(on_release=lambda *a: self.open_settings())
        topbar.add_widget(self.settings_btn)
        root.add_widget(topbar)

        # ---- 标题区（顶部）----
        head = BoxLayout(orientation="vertical", size_hint_y=None, height=160, spacing=8)
        self.title = Label(text=tr("app.name"), font_size="36sp", bold=True,
                           halign="center", valign="middle", size_hint_y=None, height=88)
        self.subtitle = Label(text=tr("home.subtitle"), font_size="15sp",
                              color=_app().theme.text_muted, halign="center",
                              valign="middle", size_hint_y=None, height=40)
        # 强调色渐变装饰条，置于标题下方
        self._accent_bar = self._accent_bar_widget()
        head.add_widget(self.title)
        head.add_widget(self._accent_bar)
        head.add_widget(self.subtitle)
        root.add_widget(head)

        # 弹性空白：让主选择区在竖直方向居中
        root.add_widget(BoxLayout(size_hint_y=1))

        # ---- 主选择区：2 阶 / 3 阶 / 4 阶（大卡片按钮）----
        from kivy.uix.gridlayout import GridLayout
        self.cards = GridLayout(cols=4, spacing=20, size_hint=(1.0, None),
                                padding=0, height=self._card_height())
        b2 = self._card("2", tr("home.card.2.title"), tr("home.card.2.desc"), onClick=lambda *a: self.pick(2))
        b3 = self._card("3", tr("home.card.3.title"), tr("home.card.3.desc"), onClick=lambda *a: self.pick(3))
        b4 = self._card("4", tr("home.card.4.title"), tr("home.card.4.desc"), onClick=lambda *a: self.pick(4))
        b5 = self._card("5", tr("home.card.5.title"), tr("home.card.5.desc"), onClick=lambda *a: self.pick(5))
        for b in (b2, b3, b4, b5):
            self.cards.add_widget(b)
        self._cards = {2: b2, 3: b3, 4: b4, 5: b5}
        root.add_widget(self.cards)
        # 横屏 1×4，竖屏 2×2；监听窗口尺寸变化重排。
        from kivy.core.window import Window
        self._last_win_size = None
        Window.bind(size=self._relayout)
        Clock.schedule_once(self._relayout, 0.1)
        # 兜底轮询：Kivy 的 Window.size 事件在部分平台（尤其 Android 转屏、
        # 或以代码方式改尺寸）不触发，主动周期性比对，尺寸变了才重排。
        Clock.schedule_interval(self._poll_layout, 0.2)

        # 弹性空白
        root.add_widget(BoxLayout(size_hint_y=1))

        # ---- 底部版本 ----
        bottom = AnchorLayout(size_hint_y=None, height=40)
        self._ver_label = Label(text=tr("home.version", version=Config.app_version),
                                font_size="13sp",
                                color=_app().theme.text_faint, halign="center", valign="middle")
        bottom.add_widget(self._ver_label)
        root.add_widget(bottom)

        self.add_widget(root)

    def retranslate(self):
        """语言切换后刷新文案。"""
        if not hasattr(self, "title"):
            return
        self.title.text = tr("app.name")
        self.subtitle.text = tr("home.subtitle")
        self._ver_label.text = tr("home.version", version=Config.app_version)
        for n, card in getattr(self, "_cards", {}).items():
            try:
                _big, title_label = card._labels
                title_label.text = tr(f"home.card.{n}.title")
            except Exception:
                pass

    def open_settings(self):
        self.manager.current = "SettingsScreen"

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

    def _accent_bar_widget(self):
        """标题下的强调色渐变装饰条。"""
        from kivy.uix.widget import Widget
        from kivy.graphics.instructions import InstructionGroup
        from ui.widgets import fx
        bar = Widget(size_hint_y=None, height=4)
        bar._grad_grp = InstructionGroup()
        bar.canvas.before.add(bar._grad_grp)

        def _draw(*a):
            theme = _app().theme
            g = bar._grad_grp
            g.clear()
            g.add(fx.gradient(theme.accent, theme.accent_dim, bar.pos, bar.size, radius=2))

        bar._draw = _draw
        bar.bind(pos=_draw, size=_draw)
        _draw()
        return bar

    def _card_draw(self, card):
        """绘制卡片背景：柔和投影 + 渐变填充 + 描边 + 顶部高光。"""
        from kivy.graphics import Color, Line, RoundedRectangle
        from ui.widgets import fx
        theme = _app().theme
        bg = getattr(card, "_bg", None)
        if bg is None:
            return
        bg.clear()
        pressed = getattr(card, "_pressed", False)
        # 柔和投影
        for inst in fx.soft_shadow(card.pos, card.size, 16, theme.card_shadow,
                                   layers=3, spread=4.0, blur=7.0):
            bg.add(inst)
        # 圆角实心底
        base = theme.surface_hi if pressed else theme.surface
        bg.add(Color(*base))
        bg.add(RoundedRectangle(pos=card.pos, size=card.size, radius=[16] * 4))
        # 描边
        bg.add(Color(*theme.card_border))
        bg.add(Line(width=1.4, rounded_rectangle=(
            card.x + 0.7, card.y + 0.7, card.width - 1.4, card.height - 1.4, 16)))

    def _card_press(self, card, touch, down):
        if not card.collide_point(*touch.pos):
            return False
        card._pressed = down
        self._card_draw(card)
        if (not down) and getattr(card, "_on_click", None) is not None:
            card._on_click()
        return False

    def _card(self, big, title, desc, onClick):
        """创建一个卡片式按钮（大号强调数字 + 标题）。"""
        from kivy.graphics.instructions import InstructionGroup
        theme = _app().theme
        card = BoxLayout(orientation="vertical", spacing=2, padding=10)
        card._pressed = False
        card._on_click = onClick
        card._bg = InstructionGroup()
        card.canvas.before.add(card._bg)
        card.bind(pos=lambda *a: self._card_draw(card),
                  size=lambda *a: self._card_draw(card))
        card.bind(on_touch_down=lambda inst, touch, c=card: self._card_press(c, touch, True),
                  on_touch_up=lambda inst, touch, c=card: self._card_press(c, touch, False))
        # 用 size_hint 比例占满卡片，避免固定高度导致文字重叠
        big_label = Label(text=big, font_size="54sp", bold=True, halign="center",
                          valign="middle", color=theme.accent, size_hint_y=0.6)
        title_label = Label(text=title, font_size="20sp", bold=True, halign="center",
                            valign="middle", color=theme.text, size_hint_y=0.4)
        card.add_widget(big_label)
        card.add_widget(title_label)
        card._labels = (big_label, title_label)
        self._card_draw(card)
        return card

    def refresh_theme(self):
        """主题切换后刷新 Python 端硬编码的颜色。"""
        theme = _app().theme
        self.subtitle.color = theme.text_muted
        self._ver_label.color = theme.text_faint
        # 强调色装饰条
        bar = getattr(self, "_accent_bar", None)
        if bar is not None and getattr(bar, "_draw", None) is not None:
            bar._draw()
        cards = getattr(self, "cards", None)
        if cards:
            for card in cards.children:
                try:
                    big, title = card._labels
                    big.color = theme.accent
                    title.color = theme.text
                    self._card_draw(card)
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


def _app():
    from kivy.app import App
    return App.get_running_app()
