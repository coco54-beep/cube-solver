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

from pathlib import Path

# Rendered 3D thumbnails (tools/export_puzzle_thumbs.py) shown on each card.
PUZZLE_IMG_DIR = Path(__file__).resolve().parents[2] / "assets" / "puzzles"


def puzzle_image(key):
    path = PUZZLE_IMG_DIR / f"{key}.png"
    return str(path) if path.exists() else None


PUZZLES = ("pyraminx", "mastermorphix", "skewb", "dino", "megaminx", "moyu", "mirror",
           "fto", "football", "icosahedron", "war_drum", "pentahedron")
SPECIAL_PUZZLES = ('eight_petals', 'clover', 'blossom', 'square1', 'void_cube',
                   'void_tower', 'mirror_tower', 'axis', 'pandora', 'windmill', 'fisher', 'ivy')
ORDERS = {'pyraminx': tuple(range(2, 8)), 'mastermorphix': tuple(range(2, 10)),
          'skewb': (3,5,7), 'dino': (2,4,6), 'megaminx': tuple(range(2, 14)),
          'moyu': tuple(range(3, 8)), 'mirror': tuple(range(2, 10))}
IMPLEMENTED_ORDERS = {**ORDERS,
                      'fto': (2, 3, 4), 'eight_petals': (3,),
                      'void_cube': (3,), 'void_tower': (3,), 'clover': (3,), 'blossom': (3,),
                      'football':(3,5), 'icosahedron':(2,3,4,5), 'ivy':(3,),
                      'war_drum': (2,3,4,5), 'pentahedron': (2,3,4,5)}
# Physical variants are named separately where an order alone is ambiguous.
# Keep catalogue ranges separate from IMPLEMENTED_ORDERS until engines exist.
ORDERS.update(fto=(2, 3, 4), football=(3, 5), icosahedron=(2, 3, 4, 5))
ORDERS.update(war_drum=(2,3,4,5), pentahedron=(2,3,4,5))
ORDER_LABELS = {
    ('fto', 2): 'directory.fto_2',
    ('fto', 4): 'directory.fto_4',
    ('icosahedron', 2): 'directory.icosahedron_2',
    ('icosahedron', 3): 'directory.icosahedron_3',
    ('icosahedron', 4): 'directory.icosahedron_4',
    ('icosahedron', 5): 'directory.icosahedron_5',
    ('dino', 2): 'directory.dinosaur_order',
    ('dino', 4): 'directory.lattice_order',
    ('dino', 6): 'directory.lattice_order',
    ('skewb', 3): 'directory.skewb_3',
    ('skewb', 5): 'directory.skewb_5',
    ('skewb', 7): 'directory.skewb_7',
}
# 语言无关的两字母标记，与首页「大号文字 + 标题」的卡片结构一致。
MARKS = {'pyraminx': "Py", 'mastermorphix': "Mo", 'skewb': "Sk", 'dino': 'Di',
         'megaminx': "Mg", 'moyu': "Tw", 'mirror': "Mi", 'special': 'Sp',
         'eight_petals': '8', 'clover': '4', 'football': 'Fb', 'fto': 'FTO',
         'icosahedron': '20', 'square1': 'SQ1', 'void_cube': 'V3',
         'void_tower': 'VT', 'mirror_tower': 'MT', 'axis': 'Ax', 'pandora': 'Pa',
         'windmill': 'Wi', 'fisher': 'Fi', 'blossom': 'Bl', 'ivy': 'Iv',
         'war_drum': 'Wd', 'pentahedron': 'Pe'}


class IrregularDirectoryScreen(Screen):
    """Lists shape-mod puzzles and lets the user choose an order."""

    puzzle_keys = PUZZLES
    title_key = 'directory.title'
    hint_key = 'directory.group_hint'
    parent_screen = 'HomeScreen'

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
        back.bind(on_release=lambda *_: setattr(self.manager, "current", self.parent_screen))
        top.add_widget(back)
        self._special_button = None
        if self.puzzle_keys == PUZZLES:
            top.add_widget(BoxLayout())
            self._special_button = UIButton(text=tr('directory.special'),size_hint_x=None,width=m.h(138))
            self._special_button.bind(on_release=lambda *_:self.open_order_picker('special'))
            top.add_widget(self._special_button)
        root.add_widget(top)

        # 标题 + 强调条（与首页同款头部结构）
        head = BoxLayout(orientation="vertical", size_hint_y=None, height=m.h(72),
                         spacing=m.h(4))
        self._head = head
        self._head_space = BoxLayout(size_hint_y=None)
        head.add_widget(self._head_space)
        self.title = Label(text=tr(self.title_key), font_size=m.font(24), bold=True,
                           color=_app().theme.text, halign="center", valign="middle")
        self.title.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        self.title.size_hint_y = None
        self._accent_bar = self._accent_bar_widget()
        head.add_widget(self.title)
        head.add_widget(self._accent_bar)

        self.hint = Label(text=tr(self.hint_key), size_hint_y=None, height=m.h(34),
                          font_size=m.font(13), color=_app().theme.text_muted,
                          halign="center", valign="middle")
        self.hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        head.add_widget(self.hint)
        root.add_widget(head)

        self.grid = GridLayout(cols=2, spacing=(m.h(12), m.h(12)), size_hint=(1, None))
        for key in self.puzzle_keys:
            button = HomeCard(MARKS[key], tr("directory." + key), image=puzzle_image(key),
                              on_click=lambda k=key: self.open_order_picker(k))
            self.grid.add_widget(button)
            self._buttons[key] = button
        self.scroll = ScrollView(do_scroll_x=False)
        self.scroll.add_widget(self.grid)
        root.add_widget(self.scroll)
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
        if self._special_button is not None:
            self._special_button.width = m.h(138)
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
        base_rows = 2 if size[0] > size[1] else 3
        card_height = (layout['grid_height']-(base_rows-1)*layout['gap'])/base_rows
        rows = (len(self.puzzle_keys)+self.grid.cols-1)//self.grid.cols
        self.grid.height = rows*card_height+(rows-1)*layout['gap']
        for card in self.grid.children:
            card._restyle()

    def _poll_layout(self, _dt):
        self._relayout()

    def retranslate(self):
        self.title.text = tr(self.title_key)
        self.hint.text = tr(self.hint_key)
        if self._special_button is not None:
            self._special_button.text = tr('directory.special')
        for key in self.puzzle_keys:
            self._buttons[key].set_title(tr("directory." + key))

    def refresh_theme(self):
        theme = _app().theme
        self.title.color = theme.text
        self.hint.color = theme.text_muted
        if self._special_button is not None:
            self._special_button.refresh_theme()
        bar = getattr(self, "_accent_bar", None)
        if bar is not None and getattr(bar, "_draw", None) is not None:
            bar._draw()
        for button in self._buttons.values():
            button.refresh_theme()

    def open_order_picker(self, puzzle):
        if puzzle=='mirror_tower':
            _app().new_mirror_tower()
            self.manager.current='MirrorTowerScreen'
            return
        if puzzle == 'special':
            self.manager.current = 'SpecialIrregularScreen'
            return
        if puzzle in SPECIAL_PUZZLES:
            if puzzle in ('axis','pandora','windmill','fisher'):
                _app().new_shape_cube(puzzle)
                self.manager.current='ShapeCubeScreen'
                return
            if puzzle=='square1':
                _app().new_square1()
                self.manager.current='Square1Screen'
                return
            if puzzle in IMPLEMENTED_ORDERS:
                _app().new_polyhedral(puzzle, IMPLEMENTED_ORDERS[puzzle][0])
                self.manager.current = 'PolyhedralScreen'
            else:
                self._show_pending(puzzle)
            return
        content = BoxLayout(orientation="vertical", spacing=m.h(10), padding=m.h(14))
        hint = Label(text=tr('directory.order_hint'), color=_app().theme.text_muted,
                     halign="center", valign="middle", size_hint_y=None, height=m.h(42))
        hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        content.add_widget(hint)

        orders = ORDERS[puzzle]
        rows = (len(orders) + 1) // 2
        order_grid = GridLayout(cols=2, spacing=m.h(8), size_hint_y=None,
                                height=m.h(rows * 54 + (rows - 1) * 8))
        popup = Popup(title=tr("directory." + puzzle), content=content,
                      size_hint=(.78, .72),
                      auto_dismiss=True)
        theme_popup(popup, _app().theme)
        for order in orders:
            label_key = ORDER_LABELS.get((puzzle, order), 'directory.order')
            # Order labels can be long; wrap them so narrow portrait screens do
            # not clip the name (a taller grid row gives the second line room).
            button = UIButton(text=tr(label_key, order=order),
                              halign="center", valign="middle")
            button.bind(width=lambda b, w: setattr(
                b, "text_size", (max(0, w - m.h(16)), None)))
            button.bind(on_release=lambda *_args, n=order: self.select_order(popup, puzzle, n))
            order_grid.add_widget(button)
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(order_grid)
        content.add_widget(scroll)
        popup.open()

    def select_order(self, picker, puzzle, order):
        picker.dismiss()
        if order not in IMPLEMENTED_ORDERS.get(puzzle, ()):
            self._show_pending(puzzle, order)
            return
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

    def _show_pending(self, puzzle, order=None, message=None):
        content=BoxLayout(orientation='vertical',spacing=m.h(12),padding=m.h(16))
        label=Label(text=message or tr('directory.pending'),color=_app().theme.text,
                    halign='center',valign='middle')
        label.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        content.add_widget(label)
        title=tr('directory.'+puzzle)
        if order is not None:
            title+=' · '+tr('directory.order',order=order)
        popup=Popup(title=title,content=content,size_hint=(.78,.40))
        theme_popup(popup,_app().theme)
        button=PrimaryButton(text=tr('directory.close'),size_hint_y=None,height=m.h(48))
        button.bind(on_release=lambda *_:popup.dismiss())
        content.add_widget(button)
        popup.open()


class SpecialIrregularScreen(IrregularDirectoryScreen):
    """Single-specification puzzles grouped under one directory entry."""

    puzzle_keys = SPECIAL_PUZZLES
    title_key = 'directory.special'
    hint_key = 'directory.special_hint'
    parent_screen = 'IrregularDirectoryScreen'


def _app():
    return App.get_running_app()
