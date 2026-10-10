"""异形魔方目录，风格与首页保持一致（同款卡片 + 标题强调条）。"""

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.instructions import InstructionGroup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from app.i18n import tr
from ui.widgets import metrics as m
from ui.widgets import fx
from ui.widgets.buttons import UIButton, PrimaryButton
from ui.widgets.cards import HomeCard
from ui.widgets.dialogs import theme_popup


PUZZLES = ("pyraminx", "mastermorphix", "skewb", "megaminx", "moyu", "mirror")
ORDERS = {'pyraminx': tuple(range(2, 8)), 'mastermorphix': tuple(range(2, 10)),
          'skewb': (3, 5, 7), 'megaminx': tuple(range(2, 14)),
          'moyu': tuple(range(3, 8)), 'mirror': tuple(range(2, 10))}
# 语言无关的两字母标记，与首页「大号文字 + 标题」的卡片结构一致。
MARKS = {'pyraminx': "Py", 'mastermorphix': "Mo", 'skewb': "Sk",
         'megaminx': "Mg", 'moyu': "Tw", 'mirror': "Mi"}


class IrregularDirectoryScreen(Screen):
    """Lists shape-mod puzzles and lets the user choose an order."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._buttons = {}
        self._last_window_size = None

        root = BoxLayout(orientation="vertical", spacing=m.h(10),
                         padding=[m.h(16), m.h(12), m.h(16), m.h(12)])
        self._root_layout = root

        # 顶栏（返回）
        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=m.h(48),
                        spacing=m.h(10))
        self._topbar = top
        back = UIButton(text=tr("directory.back"), size_hint_x=None, width=m.h(88))
        self._back_button = back
        back.bind(on_release=lambda *_: setattr(self.manager, "current", "HomeScreen"))
        top.add_widget(back)
        root.add_widget(top)

        # 标题 + 强调条（与首页同款头部结构）
        head = BoxLayout(orientation="vertical", size_hint_y=None, height=m.h(72),
                         spacing=m.h(4))
        self._head = head
        self._head_space = BoxLayout(size_hint_y=None)
        head.add_widget(self._head_space)
        self.title = Label(text=tr("directory.title"), font_size=m.font(24), bold=True,
                           color=_app().theme.text, halign="center", valign="middle")
        self.title.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        self.title.size_hint_y = None
        self._accent_bar = self._accent_bar_widget()
        head.add_widget(self.title)
        head.add_widget(self._accent_bar)

        self.hint = Label(text=tr("directory.hint"), size_hint_y=None, height=m.h(34),
                          font_size=m.font(13), color=_app().theme.text_muted,
                          halign="center", valign="middle")
        self.hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        head.add_widget(self.hint)
        root.add_widget(head)

        root.add_widget(BoxLayout())
        self.grid = GridLayout(cols=2, spacing=(m.h(12), m.h(12)), size_hint=(1, None))
        for key in PUZZLES:
            button = HomeCard(MARKS[key], tr("directory." + key),
                              on_click=lambda k=key: self.open_order_picker(k))
            self.grid.add_widget(button)
            self._buttons[key] = button
        root.add_widget(self.grid)
        root.add_widget(BoxLayout())
        self._bottom = BoxLayout(size_hint_y=None, height=m.h(28))
        root.add_widget(self._bottom)

        self.add_widget(root)

        Window.bind(size=self._relayout)
        Clock.schedule_once(self._relayout, 0)
        Clock.schedule_interval(self._poll_layout, .2)

    def _accent_bar_widget(self):
        from kivy.uix.widget import Widget
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

    def _relayout(self, *_args):
        size = (Window.width, Window.height)
        if size == self._last_window_size:
            return
        self._last_window_size = size
        layout = m.menu_grid_metrics(*size)
        self._root_layout.padding = layout['padding']
        self._root_layout.spacing = layout['spacing']
        self._topbar.height = layout['top_height']
        self._back_button.width = m.h(88)
        self._bottom.height = layout['bottom_height']
        self._head.height = layout['head_height']
        self._head.spacing = max(2, self._head.height * .025)
        self._head_space.height = self._head.height * .18
        self.title.height = self._head.height * .40
        self._accent_bar.height = max(3, self._head.height * .025)
        self.hint.height = self._head.height * .24
        self.title.font_size = m.font(25)
        self.hint.font_size = m.font(12)
        self.grid.cols = layout['columns']
        self.grid.spacing = (layout['gap'], layout['gap'])
        self.grid.height = layout['grid_height']
        for card in self.grid.children:
            card._restyle()

    def _poll_layout(self, _dt):
        self._relayout()

    def retranslate(self):
        self.title.text = tr("directory.title")
        self.hint.text = tr("directory.hint")
        for key in PUZZLES:
            self._buttons[key].set_title(tr("directory." + key))

    def refresh_theme(self):
        theme = _app().theme
        self.title.color = theme.text
        self.hint.color = theme.text_muted
        bar = getattr(self, "_accent_bar", None)
        if bar is not None and getattr(bar, "_draw", None) is not None:
            bar._draw()
        for button in self._buttons.values():
            button.refresh_theme()

    def open_order_picker(self, puzzle):
        content = BoxLayout(orientation="vertical", spacing=m.h(10), padding=m.h(14))
        hint = Label(text=tr("directory.order_hint"), color=_app().theme.text_muted,
                     halign="center", valign="middle", size_hint_y=None, height=m.h(42))
        hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        content.add_widget(hint)

        orders = ORDERS[puzzle]
        rows = (len(orders) + 1) // 2
        order_grid = GridLayout(cols=2, spacing=m.h(8), size_hint_y=None,
                                height=m.h(rows * 48 + (rows - 1) * 8))
        popup = Popup(title=tr("directory." + puzzle), content=content,
                      size_hint=(.78, .72),
                      auto_dismiss=True)
        theme_popup(popup, _app().theme)
        for order in orders:
            button = UIButton(text=tr("directory.order", order=order))
            button.bind(on_release=lambda *_args, n=order: self.select_order(popup, puzzle, n))
            order_grid.add_widget(button)
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(order_grid)
        content.add_widget(scroll)
        popup.open()

    def select_order(self, picker, puzzle, order):
        picker.dismiss()
        if puzzle == "mastermorphix":
            _app().new_mastermorphix(order)
            self.manager.current = "MastermorphixScreen"
            return

        if puzzle == 'mirror':
            _app().new_mirror(order)
            self.manager.current = 'MirrorScreen'
        else:
            _app().new_polyhedral(puzzle, order)
            self.manager.current = 'PolyhedralScreen'


def _app():
    return App.get_running_app()
