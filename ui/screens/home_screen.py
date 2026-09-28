"""首页：选择 3 阶 / 4 阶、使用说明、版本号（美观启动页式）。"""

from ui.widgets.buttons import GearButton
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.clock import Clock

from app.config import Config
from app.i18n import tr
from ui.widgets import metrics as m


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=8, padding=[20, 10, 20, 10])
        self._root_layout = root

        # ---- 顶栏：设置齿轮（右上角）----
        topbar = BoxLayout(orientation="horizontal", size_hint_y=None, height=m.h(44))
        self._topbar = topbar
        topbar.add_widget(BoxLayout(size_hint_x=1))
        self.settings_btn = GearButton(size_hint_x=None, width=m.h(44))
        self.settings_btn.bind(on_release=lambda *a: self.open_settings())
        topbar.add_widget(self.settings_btn)
        root.add_widget(topbar)

        # ---- 标题区（顶部）----
        head = BoxLayout(orientation="vertical", size_hint_y=None, height=132, spacing=3)
        self._head = head
        self._logo = self._logo_widget()
        self.title = Label(text=tr("app.name"), font_size="29sp", bold=True,
                           halign="center", valign="middle", size_hint_y=None, height=50)
        self.subtitle = Label(text=tr("home.subtitle"), font_size="13sp",
                              color=_app().theme.text_muted, halign="center",
                              valign="middle", size_hint_y=None, height=30)
        # 强调色渐变装饰条，置于标题下方
        self._accent_bar = self._accent_bar_widget()
        head.add_widget(self._logo)
        head.add_widget(self.title)
        head.add_widget(self._accent_bar)
        head.add_widget(self.subtitle)
        root.add_widget(head)

        # 弹性空白：让主选择区在竖直方向居中
        root.add_widget(BoxLayout(size_hint_y=1))

        # ---- 主选择区：2 阶 / 3 阶 / 4 阶（大卡片按钮）----
        from kivy.uix.gridlayout import GridLayout
        self.cards = GridLayout(cols=4, spacing=(14, 12), size_hint=(1.0, None),
                                padding=0, height=1)
        b2 = self._card("2", tr("home.card.2.title"), onClick=lambda *a: self.pick(2))
        b3 = self._card("3", tr("home.card.3.title"), onClick=lambda *a: self.pick(3))
        b4 = self._card("4", tr("home.card.4.title"), onClick=lambda *a: self.pick(4))
        b5 = self._card("5", tr("home.card.5.title"), onClick=lambda *a: self.pick(5))
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
        bottom = AnchorLayout(size_hint_y=None, height=28)
        self._bottom = bottom
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
        if not w or not h:
            return
        self._head.height = max(96, min(156, h * 0.21))
        self._head.spacing = max(2, self._head.height * 0.02)
        self._logo.height = self._head.height * 0.24
        self.title.height = self._head.height * 0.34
        self._accent_bar.height = max(3, self._head.height * 0.025)
        self.subtitle.height = self._head.height * 0.24
        self.title.font_size = f"{max(20, min(29, w / 15))}sp"
        self.subtitle.font_size = f"{max(10, min(13, w / 30))}sp"
        vertical_fixed = (self._root_layout.padding[1] + self._root_layout.padding[3]
                          + self._root_layout.spacing * 5 + self._topbar.height
                          + self._bottom.height + self._head.height)
        if w > h:
            self.cards.cols = 4
            self.cards.spacing = (12, 12)
            cell_w = max(64, (w - 40 - 36) / 4)
            self.cards.height = min(cell_w, max(64, h - vertical_fixed))
        else:
            self.cards.cols = 2
            self.cards.spacing = (14, 12)
            cell_w = max(72, (w - 40 - self.cards.spacing[0]) / 2)
            cell_h = max(64, (h - vertical_fixed - self.cards.spacing[1]) / 2)
            cell = min(cell_w, cell_h)
            self.cards.height = cell * 2 + self.cards.spacing[1]
        for card in self.cards.children:
            self._style_card(card)

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

    def _logo_widget(self):
        """A compact, language-neutral mark built from familiar cube colors."""
        from kivy.graphics import Color, Line, RoundedRectangle
        from kivy.uix.widget import Widget

        logo = Widget(size_hint_y=None, height=42)
        tiles = (
            (0.94, 0.96, 0.98, 1), (0.97, 0.80, 0.12, 1), (0.88, 0.20, 0.20, 1),
            (0.98, 0.98, 0.98, 1), (0.20, 0.67, 0.42, 1), (0.18, 0.43, 0.86, 1),
            (0.96, 0.96, 0.95, 1), (0.98, 0.55, 0.16, 1), (0.21, 0.65, 0.39, 1),
        )

        def draw(*_args):
            logo.canvas.clear()
            tile = min(logo.height / 3.0, 12)
            gap = max(2, tile * 0.11)
            side = tile * 3 + gap * 2
            left = logo.center_x - side / 2
            bottom = logo.center_y - side / 2
            with logo.canvas:
                for row in range(3):
                    for col in range(3):
                        x = left + col * (tile + gap)
                        y = bottom + (2 - row) * (tile + gap)
                        Color(*tiles[row * 3 + col])
                        RoundedRectangle(pos=(x, y), size=(tile, tile), radius=[tile * 0.18] * 4)
                        Color(0.12, 0.17, 0.24, 0.12)
                        Line(rounded_rectangle=(x, y, tile, tile, tile * 0.18), width=0.8)

        logo.bind(pos=draw, size=draw)
        draw()
        return logo

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
        for inst in fx.soft_shadow(card.pos, card.size, 18, theme.card_shadow,
                                   layers=2, spread=2.0, blur=3.0):
            bg.add(inst)
        # 圆角实心底
        base = theme.surface_hi if pressed else theme.surface
        bg.add(Color(*base))
        bg.add(RoundedRectangle(pos=card.pos, size=card.size, radius=[18] * 4))
        # 描边
        bg.add(Color(*theme.card_border))
        bg.add(Line(width=1.4, rounded_rectangle=(
            card.x + 0.7, card.y + 0.7, card.width - 1.4, card.height - 1.4, 18)))

    def _card_press(self, card, touch, down):
        if not card.collide_point(*touch.pos):
            return False
        card._pressed = down
        self._card_draw(card)
        if (not down) and getattr(card, "_on_click", None) is not None:
            card._on_click()
        return False

    def _card(self, big, title, onClick):
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
        big_label = Label(text=big, font_size="46sp", bold=True, halign="center",
                          valign="middle", color=theme.accent, size_hint_y=0.62)
        title_label = Label(text=title, font_size="18sp", bold=True, halign="center",
                            valign="middle", color=theme.text, size_hint_y=0.38)
        card.add_widget(big_label)
        card.add_widget(title_label)
        card._labels = (big_label, title_label)
        card.bind(size=lambda *_args, c=card: self._style_card(c))
        self._card_draw(card)
        return card

    def _style_card(self, card):
        labels = getattr(card, "_labels", None)
        if not labels:
            return
        big, title = labels
        big.font_size = f"{max(28, min(46, card.height * 0.32))}sp"
        title.font_size = f"{max(14, min(18, card.height * 0.13))}sp"
        card.padding = max(6, min(10, card.height * 0.055))

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
