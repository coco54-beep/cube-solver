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
           "fto", "football", "icosahedron", "war_drum", "pentahedron", "sq_family", "circle_family",
           "cuboid_family", "windmill", "axis", "fisher", "edge_family", "void_family",
           "penrose_family", "bandaged_family", "mosaic_family", "ivy_family", "special")
EDGE_TURNING_PUZZLES = ('petal_tetrahedron','petal_tetrahedron_nocentre', 'helicopter', 'clover', 'blossom', 'petal_icosahedron', 'petal_icosahedron_nocentre')
CUBE_PATTERN_VARIANTS = {
    'penrose_2': 2, 'penrose_3': 3, 'penrose_4': 4,
    'circle_2': 2,
    'fused_cube': 3, 'two_bar_cube': 3, 'bandaged_c': 3, 'bicube': 3,
    'ai_cube': 4, 'burr_cube': 4,
}
PENROSE_SERIES = ('penrose_2', 'penrose_3', 'penrose_4')
BANDAGED_SERIES = ('fused_cube', 'two_bar_cube', 'bandaged_c', 'bicube', 'ai_cube', 'burr_cube')
MOSAIC_SERIES = ('mosaic', 'tins')
IVY_SERIES = ('ivy', 'super_ivy', 'eight_petals')
# 只有确实没有同系列可归的独立型号才留在“特殊异形”。
SPECIAL_PUZZLES = ('pandora', 'pyraminx_duo', 'coin_tetrahedron', 'camouflage_3')
# 系列卡没有独立缩略图时借用最能代表该系列的一张。
SERIES_IMAGES = {
    'void_family': 'void_cube',
    'penrose_family': 'penrose_3',
    'bandaged_family': 'bicube',
    'mosaic_family': 'mosaic',
    'ivy_family': 'super_ivy',
}
# (family, option) -> (physical kind, order, entry screen, label).
# The Mirror and Void cards collect all appearance variants; their base
# mechanism series only list the ordinary models.
MIRROR_FAMILY_VARIANTS = {
    ('mirror','mirror_pyraminx3'): ('mirror_pyraminx',3,'MirrorPyraminxScreen','directory.mirror_pyraminx3'),
    ('mirror','mirror_pyraminx4'): ('mirror_pyraminx',4,'MirrorPyraminxScreen','directory.mirror_pyraminx4'),
    ('mirror','mirror_skewb3'): ('mirror_skewb',3,'MirrorSkewbScreen','directory.mirror_skewb3'),
    ('mirror','mirror_tower3'): ('mirror_tower',3,'MirrorTowerScreen','directory.mirror_tower3'),
    ('mirror','mirror_axis3'): ('mirror_axis',3,'MirrorAxisScreen','directory.mirror_axis3'),
    ('mirror','mirror_windmill3'): ('mirror_windmill',3,'MirrorWindmillScreen','directory.mirror_windmill_equal'),
    ('mirror','mirror_windmill_height'): ('mirror_windmill_unequal',3,'MirrorUnequalWindmillScreen','directory.mirror_windmill_unequal'),
    ('mirror','mirror_windmill_offset'): ('mirror_windmill_offset',3,'MirrorOffsetWindmillScreen','directory.mirror_windmill_offset'),
    ('mirror','mirror_fisher3'): ('mirror_fisher',3,'MirrorFisherScreen','directory.mirror_fisher_equal'),
    ('mirror','mirror_fisher_height'): ('mirror_fisher_unequal',3,'MirrorUnequalFisherScreen','directory.mirror_fisher_unequal'),
    ('mirror','mirror_fisher_offset'): ('mirror_fisher_offset',3,'MirrorOffsetFisherScreen','directory.mirror_fisher_offset'),
}
VOID_FAMILY_VARIANTS = {
    ('void_family','void_cube'): ('void_cube',3,'PolyhedralScreen','directory.void_cube'),
    ('void_family','void_tower'): ('void_tower',3,'PolyhedralScreen','directory.void_tower'),
    ('void_family','void_minx'): ('void_minx',3,'PolyhedralScreen','directory.void_minx'),
}
PUZZLE_VARIANTS = {**MIRROR_FAMILY_VARIANTS, **VOID_FAMILY_VARIANTS}
ORDERS = {'cube': tuple(range(2, MAX_N+1)),
          'pyraminx': tuple(range(2, 8)), 'mastermorphix': tuple(range(2, 10)),
          'axis': (3,4), 'windmill': (3,4), 'fisher': (3,4),
          'ghost': (1, 2, 3, 4, 'ghost_pyramid'), 'sq_family': ('square0','square1','square2','super_square1'),
          'circle_family': ('circle_2','crazy_mercury','crazy_venus','crazy_earth','crazy_mars','crazy_jupiter','crazy_saturn','crazy_uranus','crazy_neptune'),
          'cuboid_family': ('cuboid_332','cuboid_223','cuboid_334','cuboid_224','cuboid_442','cuboid_234','cuboid_133','cuboid_335','cuboid_446'),
          'skewb': (3,5,7,'skewb_ultimate','fisher_skewb'),
          'dino': (2,4,6,'4c','dino_skewb','dayan_dino_skewb'),
          'megaminx': tuple(range(2, 14)),
          'moyu': tuple(range(3, 8)), 'mirror': tuple(range(2, 10)),
          'skewb_ultimate': (3,), 'void_minx': (3,), 'void_family': (),
          'penrose_family': PENROSE_SERIES, 'bandaged_family': BANDAGED_SERIES,
          'mosaic_family': MOSAIC_SERIES, 'ivy_family': IVY_SERIES}
for _family, _option in PUZZLE_VARIANTS:
    ORDERS[_family] += (_option,)
# Appearance variants are selected from their own Mirror/Void cards.
for _family, _options in (
    ('pyraminx', ('mirror3', 'mirror4')),
    ('skewb', ('mirror3',)),
    ('axis', ('mirror3',)),
    ('windmill', ('mirror3', 'mirror_height', 'mirror_offset')),
    ('fisher', ('mirror3', 'mirror_height', 'mirror_offset')),
    ('cube', ('void3',)),
    ('moyu', ('mirror3', 'void3')),
    ('megaminx', ('void3',)),
):
    ORDERS[_family] = tuple(option for option in ORDERS[_family]
                            if option not in _options)
IMPLEMENTED_ORDERS = {**ORDERS,
                      'fto': (2, 3, 4, 5), 'eight_petals': (3,), 'helicopter': (3,), 'mosaic': (4,), 'tins': (5,), 'dino_skewb': (4,), 'dayan_dino_skewb': (4,), 'fisher_skewb': (3,),
                      'void_cube': (3,), 'void_tower': (3,), 'clover': (3,), 'blossom': (3,), 'petal_tetrahedron': (3,), 'petal_tetrahedron_nocentre': (3,), 'petal_icosahedron': (3,), 'petal_icosahedron_nocentre': (3,), 'super_ivy': (3,),
                      'football':(3,5), 'icosahedron':(2,3,4,5), 'ivy':(3,), 'pyraminx_duo':(3,), 'ghost_pyramid':(3,), 'coin_tetrahedron':(3,),
                      'war_drum': (2,3,4,5), 'pentahedron': (2,3,4,5)}
# Physical variants are named separately where an order alone is ambiguous.
# Keep catalogue ranges separate from IMPLEMENTED_ORDERS until engines exist.
ORDERS.update(fto=(2, 3, 4, 5), football=(3, 5), icosahedron=(2, 3, 4, 5))
ORDERS.update(war_drum=(2,3,4,5), pentahedron=(2,3,4,5))
ORDER_LABELS = {
    ('sq_family','square0'): 'directory.square0',
    ('sq_family','square1'): 'directory.square1',
    ('sq_family','square2'): 'directory.square2',
    ('sq_family','super_square1'): 'directory.super_square1',
    ('ghost', 1): 'ghost.first_order',
    ('fto', 2): 'directory.fto_2',
    ('fto', 4): 'directory.fto_4',
    ('fto', 5): 'directory.fto_5',
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
ORDER_LABELS.update({('circle_family',kind): 'directory.'+kind for kind in ORDERS['circle_family']})
ORDER_LABELS.update({('cuboid_family',kind): 'directory.'+kind for kind in ORDERS['cuboid_family']})
for _series, _options in (('penrose_family', PENROSE_SERIES),
                          ('bandaged_family', BANDAGED_SERIES),
                          ('mosaic_family', MOSAIC_SERIES),
                          ('ivy_family', IVY_SERIES)):
    ORDER_LABELS.update({(_series, option): 'directory.'+option
                         for option in _options})
ORDER_LABELS.update({
    ('skewb', 'skewb_ultimate'): 'directory.skewb_ultimate',
    ('skewb', 'fisher_skewb'): 'directory.fisher_skewb',
    ('dino', 'dino_skewb'): 'directory.dino_skewb',
    ('dino', 'dayan_dino_skewb'): 'directory.dayan_dino_skewb',
    ('ghost', 'ghost_pyramid'): 'directory.ghost_pyramid',
})
# 语言无关的两字母标记，与首页「大号文字 + 标题」的卡片结构一致。
MARKS = {'cube': '普', 'pyraminx': "Py", 'mirror_pyraminx': 'MP', 'ghost': 'Gh', 'mastermorphix': "Mo", 'skewb': "Sk", 'dino': 'Di',
         'sq_family':'SQ', 'circle_family':'○', 'cuboid_family':'▭', 'edge_family':'180°',
         'megaminx': "Mg", 'moyu': "Tw", 'mirror': "Mi", 'special': '特',
         'eight_petals': '8', 'helicopter': 'HC', 'clover': '4', 'football': 'Fb', 'fto': 'FTO',
         'icosahedron': '20', 'square1': 'SQ1', 'void_cube': 'V3',
         'void_tower': 'VT', 'mirror_tower': 'MT', 'axis': 'Ax', 'pandora': 'Pa',
         'windmill': 'Wi', 'fisher': 'Fi', 'blossom': 'Bl', 'ivy': 'Iv', 'skewb_ultimate': 'SU', 'void_minx': 'VM', 'super_ivy': 'SI', 'penrose_2': 'P2', 'penrose_3': 'P3', 'penrose_4': 'P4', 'camouflage_3': 'CF', 'circle_2': 'C2', 'fused_cube': 'Fu', 'two_bar_cube': '2B', 'bandaged_c': 'BC', 'bicube': 'Bi', 'ai_cube': 'AI', 'burr_cube': 'Bu',
         'mirror_windmill': 'MW', 'mirror_axis': 'MA', 'mirror_fisher': 'MF', 'mirror_skewb': 'MS',
         'war_drum': 'Wd', 'pentahedron': 'Pe', 'mosaic': 'Mo', 'tins': 'Ti', 'dino_skewb': 'DS', 'dayan_dino_skewb': 'DF', 'fisher_skewb': 'FS', 'pyraminx_duo': 'PD', 'ghost_pyramid': 'GP', 'coin_tetrahedron': 'CT',
         'penrose_family': 'P', 'bandaged_family': 'Bd', 'mosaic_family': 'MT', 'ivy_family': '叶', 'void_family': 'V'}


class IrregularDirectoryScreen(Screen):
    """Lists shape-mod puzzles and lets the user choose an order."""

    puzzle_keys = PUZZLES
    title_key = 'directory.title'
    hint_key = 'directory.group_hint'
    parent_screen = 'HomeScreen'
    menu_top_px = 44
    menu_bottom_px = 28

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
                              image=None if key == 'special' else puzzle_image(SERIES_IMAGES.get(key, key)),
                              on_click=lambda k=key: self._open_series(k))
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
        layout = m.menu_grid_metrics(*size, items=len(self.puzzle_keys),
                                     top_px=self.menu_top_px,
                                     bottom_px=self.menu_bottom_px)
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
        self.grid.height = layout['grid_height']
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

    def _open_series(self, series):
        app = _app()
        if app is not None:
            app.selection_series = series
        self.open_order_picker(series)

    def open_order_picker(self, puzzle):
        if puzzle == 'camouflage_3':
            _app().new_polyhedral(puzzle,3)
            _app().root.current='PolyhedralScreen'
            return
        if puzzle in CUBE_PATTERN_VARIANTS:
            _app().new_cube_variant(puzzle, CUBE_PATTERN_VARIANTS[puzzle])
            self.manager.current = 'InputScreen'
            return
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
        model_series = ('skewb', 'dino', 'ghost', 'penrose_family',
                        'bandaged_family', 'mosaic_family', 'ivy_family')
        hint_key = ('directory.cuboid_hint' if puzzle == 'cuboid_family' else
                    'directory.circle_hint' if puzzle == 'circle_family' else
                    'directory.edge_hint' if puzzle == 'edge_family' else
                    'directory.special_hint' if puzzle == 'special' else
                    'directory.variant_hint' if has_variants or puzzle in model_series
                    else 'directory.order_hint')
        hint = Label(text=tr(hint_key), color=_app().theme.text_muted,
                     halign="center", valign="middle", size_hint_y=None, height=m.h(42))
        hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        content.add_widget(hint)

        orders = (EDGE_TURNING_PUZZLES if puzzle == 'edge_family' else
                  SPECIAL_PUZZLES if puzzle == 'special' else ORDERS[puzzle])
        rows = (len(orders) + 1) // 2
        row_height = 76 if (has_variants
                            or puzzle in model_series
                            or puzzle in ('circle_family','cuboid_family')) else 54
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
            label=tr(label_key, order=physical_order)
            if puzzle == 'circle_family' and order.startswith('crazy_'):
                from cube.circle_cube import PLANETS,FACES
                fixed='/'.join(face for face in FACES if face not in PLANETS[order[6:]])
                label+='\n'+tr('directory.circle_fixed',faces=fixed)
            button = UIButton(text=label,
                              halign="center", valign="middle")
            button.bind(width=lambda b, w: setattr(
                b, "text_size", (max(0, w - m.h(16)), None)))
            button.bind(on_release=lambda *_args, n=order: self.select_order(popup, puzzle, n))
            order_grid.add_widget(button)
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(order_grid)
        content.add_widget(scroll)
        back = UIButton(text=tr('directory.back'), size_hint_y=None, height=m.h(40))
        back.bind(on_release=lambda *_: popup.dismiss())
        content.add_widget(back)
        popup.open()

    def select_order(self, picker, puzzle, order):
        picker.dismiss()
        if puzzle == 'penrose_family':
            _app().new_cube_variant(order, CUBE_PATTERN_VARIANTS[order])
            self.manager.current = 'InputScreen'
            return
        if puzzle == 'bandaged_family':
            _app().new_cube_variant(order, CUBE_PATTERN_VARIANTS[order])
            self.manager.current = 'InputScreen'
            return
        if puzzle == 'mosaic_family':
            _app().new_polyhedral(order, 4 if order == 'mosaic' else 5)
            self.manager.current = 'PolyhedralScreen'
            return
        if puzzle == 'ivy_family':
            _app().new_polyhedral(order, 3)
            self.manager.current = 'PolyhedralScreen'
            return
        if puzzle == 'cuboid_family':
            if order in ORDERS[puzzle]:
                _app().new_polyhedral(order,3)
                self.manager.current='PolyhedralScreen'
            return
        if puzzle == 'circle_family':
            if order not in ORDERS[puzzle]:
                return
            if order == 'circle_2':
                _app().new_cube_variant(order,2)
                self.manager.current='InputScreen'
            else:
                _app().new_polyhedral(order,3)
                self.manager.current='PolyhedralScreen'
            return
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
        if puzzle == 'skewb':
            if order == 'skewb_ultimate':
                _app().new_polyhedral(order, 3)
                self.manager.current = 'PolyhedralScreen'
                return
            if order == 'fisher_skewb':
                _app().new_fisher_skewb()
                self.manager.current = 'FisherSkewbScreen'
                return
        if puzzle == 'dino':
            if order in ('dino_skewb', 'dayan_dino_skewb'):
                _app().new_polyhedral(order, 4)
                self.manager.current = 'PolyhedralScreen'
                return
            if order == '4c':
                _app().new_polyhedral('dino4', 2)
                self.manager.current = 'PolyhedralScreen'
                return
        if puzzle == 'ghost' and order == 'ghost_pyramid':
            _app().new_ghost_pyramid()
            self.manager.current = 'GhostPyramidScreen'
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
