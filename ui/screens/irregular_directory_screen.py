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
from cube.cube_n import MAX_N

# Rendered 3D thumbnails (tools/export_puzzle_thumbs.py) shown on each card.
PUZZLE_IMG_DIR = Path(__file__).resolve().parents[2] / "assets" / "puzzles"


def puzzle_image(key):
    path = PUZZLE_IMG_DIR / f"{key}.png"
    return str(path) if path.exists() else None


PUZZLES = ("pyraminx", "mastermorphix", "skewb", "dino", "megaminx", "moyu", "mirror", "ghost",
           "fto", "football", "icosahedron", "war_drum", "pentahedron", "sq_family", "windmill", "axis", "fisher", "edge_family", "special")
EDGE_TURNING_PUZZLES = ('petal_tetrahedron','petal_tetrahedron_nocentre', 'clover', 'blossom', 'petal_icosahedron', 'petal_icosahedron_nocentre')
SPECIAL_PUZZLES = ('eight_petals', 'ivy', 'pandora', 'skewb_ultimate')
# (family, option) -> (physical kind, order, entry screen, label).
# Mirror shape mods live under their ordinary family; the original Mirror
# Cube remains a standalone family with its existing order range.
MIRROR_VARIANTS = {
    ('axis','mirror3'): ('mirror_axis',3,'MirrorAxisScreen','directory.mirror_order'),
    ('windmill','mirror3'): ('mirror_windmill',3,'MirrorWindmillScreen','mirror.variant.equal'),
    ('windmill','mirror_height'): ('mirror_windmill_unequal',3,'MirrorUnequalWindmillScreen','mirror.variant.unequal'),
    ('windmill','mirror_offset'): ('mirror_windmill_offset',3,'MirrorOffsetWindmillScreen','mirror.variant.offset'),
    ('fisher','mirror3'): ('mirror_fisher',3,'MirrorFisherScreen','mirror.variant.equal'),
    ('fisher','mirror_height'): ('mirror_fisher_unequal',3,'MirrorUnequalFisherScreen','mirror.variant.unequal'),
    ('fisher','mirror_offset'): ('mirror_fisher_offset',3,'MirrorOffsetFisherScreen','mirror.variant.offset'),
    ('pyraminx','mirror3'): ('mirror_pyraminx',3,'MirrorPyraminxScreen','directory.mirror_order'),
    ('pyraminx','mirror4'): ('mirror_pyraminx',4,'MirrorPyraminxScreen','directory.mirror_order'),
    ('skewb','mirror3'): ('mirror_skewb',3,'MirrorSkewbScreen','directory.mirror_order'),
    ('moyu','mirror3'): ('mirror_tower',3,'MirrorTowerScreen','directory.mirror_order'),
}
VOID_VARIANTS = {
    ('cube','void3'): ('void_cube',3,'PolyhedralScreen','directory.void_cube'),
    ('moyu','void3'): ('void_tower',3,'PolyhedralScreen','directory.void_tower'),
    ('megaminx','void3'): ('void_minx',3,'PolyhedralScreen','directory.void_minx'),
}
PUZZLE_VARIANTS = {**MIRROR_VARIANTS, **VOID_VARIANTS}
ORDERS = {'cube': tuple(range(2, MAX_N+1)),
          'pyraminx': tuple(range(2, 8)), 'mastermorphix': tuple(range(2, 10)),
          'axis': (3,4), 'windmill': (3,4), 'fisher': (3,4),
          'ghost': (1, 2, 3, 4), 'sq_family': ('square0','square1','square2','super_square1'),
          'skewb': (3,5,7), 'dino': (2,4,6,'4c'), 'megaminx': tuple(range(2, 14)),
          'moyu': tuple(range(3, 8)), 'mirror': tuple(range(2, 10)),
          'skewb_ultimate': (3,), 'void_minx': (3,)}
for _family, _option in PUZZLE_VARIANTS:
    ORDERS[_family] += (_option,)
IMPLEMENTED_ORDERS = {**ORDERS,
                      'fto': (2, 3, 4), 'eight_petals': (3,),
                      'void_cube': (3,), 'void_tower': (3,), 'clover': (3,), 'blossom': (3,), 'petal_tetrahedron': (3,), 'petal_tetrahedron_nocentre': (3,), 'petal_icosahedron': (3,), 'petal_icosahedron_nocentre': (3,),
                      'football':(3,5), 'icosahedron':(2,3,4,5), 'ivy':(3,),
                      'war_drum': (2,3,4,5), 'pentahedron': (2,3,4,5)}
# Physical variants are named separately where an order alone is ambiguous.
# Keep catalogue ranges separate from IMPLEMENTED_ORDERS until engines exist.
ORDERS.update(fto=(2, 3, 4), football=(3, 5), icosahedron=(2, 3, 4, 5))
ORDERS.update(war_drum=(2,3,4,5), pentahedron=(2,3,4,5))
ORDER_LABELS = {
    ('sq_family','square0'): 'directory.square0',
    ('sq_family','square1'): 'directory.square1',
    ('sq_family','square2'): 'directory.square2',
    ('sq_family','super_square1'): 'directory.super_square1',
    ('ghost', 1): 'ghost.first_order',
    ('fto', 2): 'directory.fto_2',
    ('fto', 4): 'directory.fto_4',
    ('icosahedron', 2): 'directory.icosahedron_2',
    ('icosahedron', 3): 'directory.icosahedron_3',
    ('icosahedron', 4): 'directory.icosahedron_4',
    ('icosahedron', 5): 'directory.icosahedron_5',
    ('dino', 2): 'directory.dinosaur_order',
    ('dino', 4): 'directory.lattice_order',
    ('dino', 6): 'directory.lattice_order',
    ('dino', '4c'): 'directory.dino_four',
    ('skewb', 3): 'directory.skewb_3',
    ('skewb', 5): 'directory.skewb_5',
    ('skewb', 7): 'directory.skewb_7',
}
ORDER_LABELS.update({key: variant[3] for key, variant in PUZZLE_VARIANTS.items()})
# 语言无关的两字母标记，与首页「大号文字 + 标题」的卡片结构一致。
MARKS = {'cube': '普', 'pyraminx': "Py", 'mirror_pyraminx': 'MP', 'ghost': 'Gh', 'mastermorphix': "Mo", 'skewb': "Sk", 'dino': 'Di',
         'sq_family':'SQ', 'edge_family':'180°',
         'megaminx': "Mg", 'moyu': "Tw", 'mirror': "Mi", 'special': '特',
         'eight_petals': '8', 'clover': '4', 'football': 'Fb', 'fto': 'FTO',
         'icosahedron': '20', 'square1': 'SQ1', 'void_cube': 'V3',
         'void_tower': 'VT', 'mirror_tower': 'MT', 'axis': 'Ax', 'pandora': 'Pa',
         'windmill': 'Wi', 'fisher': 'Fi', 'blossom': 'Bl', 'ivy': 'Iv', 'skewb_ultimate': 'SU', 'void_minx': 'VM',
         'mirror_windmill': 'MW', 'mirror_axis': 'MA', 'mirror_fisher': 'MF', 'mirror_skewb': 'MS',
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
        self._back_button = None
        self._build_topbar(top)
        root.add_widget(top)

        # 标题 + 强调条（与首页同款头部结构）
        head = BoxLayout(orientation="vertical", size_hint_y=None, height=m.h(72),
                         spacing=m.h(4))
        self._head = head
        self._head_space = BoxLayout(size_hint_y=None)
        head.add_widget(self._head_space)
        theme = _app().theme if _app() is not None else None
        self.title = Label(text=tr(self.title_key), font_size=m.font(24), bold=True,
                           color=getattr(theme, "text", (1, 1, 1, 1)),
                           halign="center", valign="middle")
        self.title.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        self.title.size_hint_y = None
        self._accent_bar = self._accent_bar_widget()
        head.add_widget(self.title)
        head.add_widget(self._accent_bar)

        self.hint = Label(text=tr(self.hint_key), size_hint_y=None, height=m.h(34),
                          font_size=m.font(13),
                          color=getattr(theme, "text_muted", (.7, .7, .7, 1)),
                          halign="center", valign="middle")
        self.hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        head.add_widget(self.hint)
        root.add_widget(head)

        self.grid = GridLayout(cols=2, spacing=(m.h(12), m.h(12)), size_hint=(1, None))
        for key in self.puzzle_keys:
            button = HomeCard(MARKS[key], tr("directory." + key),
                              image=None if key == 'special' else puzzle_image(key),
                              on_click=lambda k=key: self.open_order_picker(k))
            self.grid.add_widget(button)
            self._buttons[key] = button
        self.scroll = ScrollView(do_scroll_x=False)
        self.scroll.add_widget(self.grid)
        root.add_widget(self.scroll)
        self._bottom = self._build_bottom()
        root.add_widget(self._bottom)

        self.add_widget(root)

        Window.bind(size=self._relayout)
        Clock.schedule_once(self._relayout, 0)
        Clock.schedule_interval(self._poll_layout, .2)

    def _build_topbar(self, top):
        back = UIButton(text=tr('directory.back'), size_hint_x=None, width=m.h(88))
        self._back_button = back
        back.bind(on_release=lambda *_: setattr(self.manager, 'current', self.parent_screen))
        top.add_widget(back)
        top.add_widget(BoxLayout())

    def _build_bottom(self):
        return BoxLayout(size_hint_y=None, height=m.h(28))

    def _accent_bar_widget(self):
        from kivy.uix.widget import Widget
        bar = Widget(size_hint_y=None, height=4)
        bar._grad_grp = InstructionGroup()
        bar.canvas.before.add(bar._grad_grp)

        def _draw(*a):
            app = _app()
            if app is None:
                return
            theme = app.theme
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
        if self._back_button is not None:
            self._back_button.width = m.h(88)
        for button in getattr(self, '_toolbar_buttons', ()):
            button.width = button.height = layout['top_height']
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
        if self._back_button is not None:
            self._back_button.text = tr('directory.back')
        for key in self.puzzle_keys:
            self._buttons[key].set_title(tr("directory." + key))

    def refresh_theme(self):
        app = _app()
        if app is None:
            return
        theme = app.theme
        self.title.color = theme.text
        self.hint.color = theme.text_muted
        bar = getattr(self, "_accent_bar", None)
        if bar is not None and getattr(bar, "_draw", None) is not None:
            bar._draw()
        for button in self._buttons.values():
            button.refresh_theme()

    def open_order_picker(self, puzzle):
        if puzzle in SPECIAL_PUZZLES or puzzle in EDGE_TURNING_PUZZLES:
            if puzzle == 'pandora':
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
        has_variants = any(family == puzzle for family, _ in PUZZLE_VARIANTS)
        hint_key = ('directory.edge_hint' if puzzle == 'edge_family' else
                    'directory.special_hint' if puzzle == 'special' else
                    'directory.variant_hint' if has_variants else 'directory.order_hint')
        hint = Label(text=tr(hint_key), color=_app().theme.text_muted,
                     halign="center", valign="middle", size_hint_y=None, height=m.h(42))
        hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        content.add_widget(hint)

        orders = (EDGE_TURNING_PUZZLES if puzzle == 'edge_family' else
                  SPECIAL_PUZZLES if puzzle == 'special' else ORDERS[puzzle])
        rows = (len(orders) + 1) // 2
        row_height = 76 if has_variants else 54
        order_grid = GridLayout(cols=2, spacing=m.h(8), size_hint_y=None,
                                height=m.h(rows * row_height + (rows - 1) * 8))
        popup = Popup(title=tr("directory." + puzzle), content=content,
                      size_hint=(.78, .72),
                      auto_dismiss=True)
        theme_popup(popup, _app().theme)
        for order in orders:
            label_key = ('edge.'+order if puzzle == 'edge_family' else
                         'directory.'+order if puzzle == 'special' else
                         ORDER_LABELS.get((puzzle, order), 'directory.order'))
            # Order labels can be long; wrap them so narrow portrait screens do
            # not clip the name (a taller grid row gives the second line room).
            variant = PUZZLE_VARIANTS.get((puzzle, order))
            physical_order = variant[1] if variant else order
            button = UIButton(text=tr(label_key, order=physical_order),
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
        if puzzle == 'edge_family':
            if order in EDGE_TURNING_PUZZLES:
                self.open_order_picker(order)
            return
        if puzzle == 'special':
            if order in SPECIAL_PUZZLES:
                self.open_order_picker(order)
            return
        variant = PUZZLE_VARIANTS.get((puzzle, order))
        if variant:
            kind, physical_order, screen, _label = variant
            if kind in ('void_cube','void_tower','void_minx'):
                _app().new_polyhedral(kind, physical_order)
            elif kind == 'mirror_pyraminx':
                _app().new_mirror_pyraminx(physical_order)
            elif kind == 'mirror_skewb':
                _app().new_mirror_skewb()
            elif kind == 'mirror_tower':
                _app().new_mirror_tower()
            else:
                _app().new_mirror_shape(kind, physical_order)
            self.manager.current = screen
            return
        if puzzle == 'sq_family':
            if order == 'square1':
                _app().new_square1()
                self.manager.current='Square1Screen'
            else:
                _app().new_square_family(order)
                self.manager.current='SquareFamilyScreen'
            return
        if puzzle == 'dino' and order == '4c':
            _app().new_polyhedral('dino4', 2)
            self.manager.current = 'PolyhedralScreen'
            return
        if order not in IMPLEMENTED_ORDERS.get(puzzle, ()):
            self._show_pending(puzzle, order)
            return
        if puzzle == 'cube':
            _app().new_cube(order)
            _app().input_from_camera = False
            self.manager.current = 'InputScreen'
            return
        if puzzle == 'ghost':
            _app().new_ghost(order)
            self.manager.current='GhostScreen'
            return
        if puzzle in ('axis','windmill','fisher'):
            _app().new_shape_cube(puzzle,order)
            self.manager.current='ShapeCubeScreen'
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


def _app():
    return App.get_running_app()
