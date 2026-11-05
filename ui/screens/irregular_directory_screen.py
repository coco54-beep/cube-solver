"""异形魔方目录，风格与首页保持一致（同款卡片 + 标题强调条）。"""

import re

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

from app.i18n import current_language, tr
from ui.widgets import metrics as m
from ui.widgets import fx
from ui.widgets.buttons import UIButton, PrimaryButton
from ui.widgets.cards import HomeCard
from ui.widgets.dialogs import theme_popup

from pathlib import Path
from cube.cube_n import MAX_N
from candidate_puzzles import (REQUESTED,BY_KIND,POLYHEDRAL_KINDS,DOGIC_KINDS,SIAMESE_KINDS,
                               PRISM_KINDS,CATALOGUE_FAMILIES,catalogue_family,PENDING_KINDS)

# Rendered 3D thumbnails (tools/export_puzzle_thumbs.py) shown on each card.
PUZZLE_IMG_DIR = Path(__file__).resolve().parents[2] / "assets" / "puzzles"


def puzzle_image(key):
    path = PUZZLE_IMG_DIR / f"{key}.png"
    return str(path) if path.exists() else None


def order_image(puzzle, order):
    """Use a real model thumbnail in the order/variant picker."""
    if isinstance(order,str) and order in PENDING_KINDS:
        return next((str(path) for suffix in ('.jpg','.png')
                     for path in (PUZZLE_IMG_DIR/'pending'/f'{order}{suffix}',) if path.is_file()),None)
    variant = PUZZLE_VARIANTS.get((puzzle, order))
    keys = []
    if variant:
        keys.append(variant[0])
    if isinstance(order, str):
        keys.append(order)
    keys.append(SERIES_IMAGES.get(puzzle, puzzle))
    for key in keys:
        image = puzzle_image(key)
        if image:
            return image
    return None


_CN_DIGITS = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
              '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}


def _cn_number(text):
    if '十' not in text:
        return _CN_DIGITS.get(text)
    left, _, right = text.partition('十')
    tens = _CN_DIGITS.get(left, 1) if left else 1
    ones = _CN_DIGITS.get(right, 0) if right else 0
    return tens * 10 + ones


def _order_number(puzzle, order, physical_order):
    if order=='kairis_star_finder':return None
    if isinstance(physical_order, int):
        return physical_order
    if isinstance(order, int):
        return order
    if puzzle in ('cuboid_family', 'circle_family', 'sq_family', 'edge_family',
                  'mixup_family', 'tangram_family', 'bandaged_family',
                  'mosaic_family', 'ivy_family', 'pentagonal_family',
                  'extended_family', 'round_family', 'special'):
        return None
    if puzzle == 'penrose_family' and isinstance(order, str):
        match = re.search(r'(\d+)$', order)
        if match:
            return int(match.group(1))
    known = {'fisher_skewb': 3, 'skewb_ultimate': 3, 'ghost_pyramid': 3}
    if isinstance(order, str) and order in known:
        return known[order]
    if isinstance(order, str):
        entry = BY_KIND.get(order)
        if entry is not None and isinstance(entry.n, int):
            return entry.n
    return None


def picker_label(puzzle, order):
    """Localized, order-first label shared by the picker and search."""
    if isinstance(order,str) and order in PENDING_KINDS:
        return tr('directory.'+order)+'\n'+tr('expanded.pending_short'),BY_KIND[order].n
    label_key = ('edge.'+order if puzzle == 'edge_family' and order in EDGE_TURNING_PUZZLES else
                 'directory.'+order if puzzle == 'special' else
                 ORDER_LABELS.get((puzzle, order), 'directory.order'))
    variant = PUZZLE_VARIANTS.get((puzzle, order))
    physical_order = variant[1] if variant else order
    label = tr(label_key, order=physical_order)
    if puzzle == 'circle_family' and order.startswith('crazy_'):
        from cube.circle_cube import PLANETS, FACES
        fixed = '/'.join(face for face in FACES if face not in PLANETS[order[6:]])
        label += '\n' + tr('directory.circle_fixed', faces=fixed)
    n = _order_number(puzzle, order, physical_order)
    if n is not None:
        label = format_order_label(label, n)
    return label, physical_order


def picker_orders(puzzle):
    """The same visible models for the family popup, search and photo menu."""
    return SPECIAL_PUZZLES if puzzle=='special' else ORDERS.get(puzzle,())


def format_order_label(label, n):
    """Put the order before the model name and use one number style."""
    text = label
    cn = r'[零一二三四五六七八九十两]+'
    patterns = (
        rf'^\s*{n}\s*(?:阶|段|層|层)\s*[·・:：\-]?\s*',
        rf'\s*[·・:：\-]?\s*{n}\s*(?:阶|段|層|层)\s*$',
        rf'^\s*Order\s*{n}\s*[·・:：\-]?\s*',
        rf'\s*[·・:：\-]?\s*Order\s*{n}\s*$',
        rf'^\s*{n}\s*[·・]\s*',
        rf'\s*[·・]\s*{n}\s*(?:layers?|層|层|段)\s*$',
        rf'\s+{n}\s*(?:layers?|層|层|段)\s*$',
        rf'\s*[·・]?\s*{n}×{n}\s*$',
        rf'\s*[（(]\s*{n}\s*(?:阶|段|層|层|layers?)\s*[）)]\s*',
        rf'^\s*{n}\s*-\s*layers?\s*',
        rf'\s*[·・]?\s*{n}\s*-\s*layers?\s*$',
    )
    for pattern in patterns:
        text = re.sub(pattern, '', text, count=1, flags=re.I)
    text = re.sub(rf'\s*[·・]\s*{n}\s*(?:段|層|层)\s*', ' ', text, count=1)
    text = re.sub(rf'(?<![\d×]){n}\s*×\s*{n}(?!\s*×)', '', text, count=1)
    for pattern in (rf'^\s*({cn})\s*阶\s*[·・:：\-]?\s*',
                    rf'\s*[·・:：\-]?\s*({cn})\s*阶\s*$',
                    rf'\s*[（(]\s*({cn})\s*阶\s*[）)]\s*'):
        match = re.search(pattern, text)
        if match and _cn_number(match.group(1)) == n:
            text = re.sub(pattern, '', text, count=1)
            break
    for pattern in (rf'^\s*({cn})\s*阶\s*[·・:：\-]?\s*',
                    rf'\s*[·・:：\-]?\s*({cn})\s*阶\s*$',
                    rf'[（(]\s*({cn})\s*阶\s*[）)]'):
        match = re.search(pattern, text)
        if match and _cn_number(match.group(1)) == n:
            text = re.sub(pattern, '', text, count=1)
            break
    # Order markers may sit inside a name (for example 镜面三阶魔塔).
    for match in re.finditer(rf'({cn})\s*阶', text):
        if _cn_number(match.group(1)) == n:
            text = text[:match.start()] + text[match.end():]
            break
    text = re.sub(r'\s{2,}', ' ', text)
    model = re.sub(r'^[\s·・:：\-]+|[\s·・:：\-]+$', '', text)
    prefix = tr('directory.order', order=n)
    return prefix if not model else f'{prefix} · {model}'


PUZZLES = ("pyraminx", "mastermorphix", "skewb", "dino", "megaminx", "moyu", "mirror", "ghost",
           "fto", "football", "icosahedron", "war_drum", "pentahedron", "sq_family", "circle_family",
           "cuboid_family", "extended_family", "pentagonal_family", "round_family",
           "windmill", "axis", "fisher", "edge_family", "void_family",
           "penrose_family", "bandaged_family", "mosaic_family", "ivy_family", "mixup_family", "tangram_family", "special")
EDGE_TURNING_PUZZLES = ('petal_tetrahedron','petal_tetrahedron_nocentre', 'helicopter', 'clover', 'blossom', 'petal_icosahedron', 'petal_icosahedron_nocentre')
CUBE_PATTERN_VARIANTS = {
    'penrose_2': 2, 'penrose_3': 3, 'penrose_4': 4,
    'fused_cube': 3, 'two_bar_cube': 3, 'bandaged_c': 3, 'bicube': 3,
    'ai_cube': 4, 'burr_cube': 4,
}
PENROSE_SERIES = ('penrose_2', 'penrose_3', 'penrose_4')
BANDAGED_SERIES = ('fused_cube', 'two_bar_cube', 'bandaged_c', 'bicube', 'ai_cube', 'burr_cube')
MOSAIC_SERIES = ('mosaic', 'tins')
IVY_SERIES = ('ivy', 'super_ivy', 'eight_petals')
# 只有确实没有同系列可归的独立型号才留在“特殊异形”。
SPECIAL_PUZZLES = ('pandora', 'pyraminx_duo', 'coin_tetrahedron', 'camouflage_3', 'o2', 'ancient_coin', 'pentacle')
# 系列卡没有独立缩略图时借用最能代表该系列的一张。
SERIES_IMAGES = {
    'void_family': 'void_cube',
    'penrose_family': 'penrose_3',
    'bandaged_family': 'bicube',
    'mosaic_family': 'mosaic',
    'ivy_family': 'super_ivy',
    'mixup_family':'mixup_333',
    'tangram_family':'tangram',
    'extended_family':'l_cube',
    'pentagonal_family':'professor_pentagonal',
    'round_family':'rubik_cheese',
}
# (family, option) -> (physical kind, order, entry screen, label).
# The Mirror and Void cards collect all appearance variants; their base
# mechanism series only list the ordinary models.
MIRROR_FAMILY_VARIANTS = {
    ('mirror','mirror_camouflage_3'): ('mirror_camouflage_3',3,'CuboidSixViewScreen','directory.mirror_camouflage_3'),
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
          'cuboid_family': ('cuboid_332','cuboid_223','cuboid_334','cuboid_224','cuboid_442','cuboid_234','floppy_133','cuboid_133','cuboid_335','cuboid_446'),
          'skewb': (3,5,7,'skewb_ultimate','fisher_skewb'),
          'dino': (2,4,6,'4c','dino_skewb','dayan_dino_skewb'),
          'megaminx': tuple(range(2, 14)),
          'moyu': tuple(range(3, 8)), 'mirror': tuple(range(2, 10)),
          'skewb_ultimate': (3,), 'void_minx': (3,), 'void_family': (),
          'penrose_family': PENROSE_SERIES, 'bandaged_family': BANDAGED_SERIES,
          'mosaic_family': MOSAIC_SERIES, 'ivy_family': IVY_SERIES}
from cube.articulated import MIXUP_MODELS,TANGRAM_MODELS
ORDERS.update(mixup_family=tuple(MIXUP_MODELS),tangram_family=TANGRAM_MODELS)
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
                      'war_drum': (2,3,4,5), 'pentahedron': (2,3,4,5), 'o2':(1,), 'ancient_coin':(3,)}
# Physical variants are named separately where an order alone is ambiguous.
# Keep catalogue ranges separate from IMPLEMENTED_ORDERS until engines exist.
ORDERS.update(fto=(2, 3, 4, 5), football=(3, 5), icosahedron=(2, 3, 4, 5))
ORDERS.update(war_drum=(2,3,4,5), pentahedron=(2,3,4,5))
for _family,_kinds in CATALOGUE_FAMILIES.items():
    ORDERS[_family]=ORDERS.get(_family,())+tuple(kind for kind in _kinds
                                               if kind not in ORDERS.get(_family,()))
    IMPLEMENTED_ORDERS[_family]=tuple(k for k in ORDERS[_family] if k not in PENDING_KINDS)
# Keep the registered physical models and the original seven edge variants
# in one list. The popup used to override this list with only those seven,
# hiding new cards even though their direct launch routes already worked.
ORDERS['edge_family']=tuple(dict.fromkeys((*ORDERS.get('edge_family',()),*EDGE_TURNING_PUZZLES)))
IMPLEMENTED_ORDERS['edge_family']=tuple(k for k in ORDERS['edge_family'] if k not in PENDING_KINDS)
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
ORDER_LABELS.update({(family,kind):'directory.'+kind for family in ('mixup_family','tangram_family') for kind in ORDERS[family]})
ORDER_LABELS.update({(family,kind):'directory.'+kind
                     for family,kinds in CATALOGUE_FAMILIES.items() for kind in kinds})
ORDER_LABELS.update({('megaminx',n):'directory.minx_order' for n in range(2,14)})
ORDER_LABELS[('megaminx',2)]='directory.kilominx_order'
ORDER_LABELS[('fto',3)]='directory.fto_3'
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
         'mixup_family':'Mx','tangram_family':'Tg','o2':'O2','ancient_coin':'币','pentacle':'★',
         'sq_family':'SQ', 'circle_family':'○', 'cuboid_family':'▭', 'edge_family':'180°',
         'megaminx': "Mg", 'moyu': "Tw", 'mirror': "Mi", 'special': '特',
         'eight_petals': '8', 'helicopter': 'HC', 'clover': '4', 'football': 'Fb', 'fto': 'FTO',
         'icosahedron': '20', 'square1': 'SQ1', 'void_cube': 'V3',
         'void_tower': 'VT', 'mirror_tower': 'MT', 'axis': 'Ax', 'pandora': 'Pa',
         'windmill': 'Wi', 'fisher': 'Fi', 'blossom': 'Bl', 'ivy': 'Iv', 'skewb_ultimate': 'SU', 'void_minx': 'VM', 'super_ivy': 'SI', 'penrose_2': 'P2', 'penrose_3': 'P3', 'penrose_4': 'P4', 'camouflage_3': 'CF', 'circle_2': 'C2', 'fused_cube': 'Fu', 'two_bar_cube': '2B', 'bandaged_c': 'BC', 'bicube': 'Bi', 'ai_cube': 'AI', 'burr_cube': 'Bu',
         'mirror_windmill': 'MW', 'mirror_axis': 'MA', 'mirror_fisher': 'MF', 'mirror_skewb': 'MS',
         'war_drum': 'Wd', 'pentahedron': 'Pe', 'mosaic': 'Mo', 'tins': 'Ti', 'dino_skewb': 'DS', 'dayan_dino_skewb': 'DF', 'fisher_skewb': 'FS', 'pyraminx_duo': 'PD', 'ghost_pyramid': 'GP', 'coin_tetrahedron': 'CT',
         'penrose_family': 'P', 'bandaged_family': 'Bd', 'mosaic_family': 'MT', 'ivy_family': '叶', 'void_family': 'V'}


MARKS.update(extended_family='L',pentagonal_family='5',round_family='●')


class PendingPuzzleCard(HomeCard):
    """Keep the pending badge visible even when the model name wraps."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._big.size_hint_y=.52;self._title.size_hint_y=.48
        self.pending_label=Label(text=tr('expanded.pending_short'),size_hint_y=None,
                                 height=m.h(18),font_size=m.font(12),color=_app().theme.text_muted)
        self.add_widget(self.pending_label)
        self._restyle()

    def _restyle(self,*args):
        super()._restyle(*args)
        self._title.font_size=min(self._title.font_size,m.font(14))
        if hasattr(self,'pending_label'):
            self.pending_label.height=m.h(18);self.pending_label.font_size=m.font(12)

    def refresh_theme(self,*args):
        super().refresh_theme(*args)
        if hasattr(self,'pending_label'):self.pending_label.color=_app().theme.text_muted


class IrregularDirectoryScreen(Screen):
    """Lists shape-mod puzzles and lets the user choose an order."""

    puzzle_keys = PUZZLES
    category_groups = {}
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
            representative = self.category_groups.get(key, (key,))[0]
            button = HomeCard(MARKS[representative], tr("directory." + key),
                              image=None if key == 'special' else puzzle_image(SERIES_IMAGES.get(representative, representative)),
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
        if series=='expanded_family':
            # Saved entry pages from the former catch-all return to their
            # actual family after upgrading, without recreating a second card.
            series=catalogue_family(getattr(_app(),'puzzle_kind',None)) or 'special'
        app = _app()
        if app is not None:
            app.selection_series = series
        self.open_order_picker(series)

    def open_order_picker(self, puzzle):
        if puzzle in PENDING_KINDS:
            self._show_pending(puzzle)
            return
        if puzzle=='pentacle':
            _app().new_pentacle()
            self.manager.current='PentacleScreen'
            return
        if puzzle in ('camouflage_3','circle_2'):
            _app().new_polyhedral(puzzle,2 if puzzle=='circle_2' else 3)
            from ui.screens.polyhedral_screen import _entry_for
            _app().root.current=_entry_for(_app().cube)
            return
        if puzzle in CUBE_PATTERN_VARIANTS:
            _app().new_cube_variant(puzzle, CUBE_PATTERN_VARIANTS[puzzle])
            self.manager.current = 'InputScreen'
            return
        if puzzle in SPECIAL_PUZZLES or puzzle in EDGE_TURNING_PUZZLES:
            if puzzle == 'pandora':
                _app().new_shape_cube(puzzle)
                self.manager.current='InputScreen'
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
        families = self.category_groups.get(puzzle, (puzzle,))
        has_variants = any(family == puzzle for family, _ in PUZZLE_VARIANTS)
        model_series = ('skewb', 'dino', 'ghost', 'penrose_family', 'mixup_family', 'tangram_family',
                        'bandaged_family', 'mosaic_family', 'ivy_family',*CATALOGUE_FAMILIES)
        hint_key = ('directory.cuboid_hint' if puzzle == 'cuboid_family' else
                    'directory.circle_hint' if puzzle == 'circle_family' else
                    'directory.edge_hint' if puzzle == 'edge_family' else
                    'directory.special_hint' if puzzle == 'special' else
                    'directory.variant_hint' if len(families) > 1 or has_variants or puzzle in model_series
                    else 'directory.order_hint')
        hint = Label(text=tr(hint_key), color=_app().theme.text_muted,
                     halign="center", valign="middle", size_hint_y=None, height=m.h(42))
        hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        content.add_widget(hint)

        options = [(family, order) for family in families for order in picker_orders(family)]
        popup_width = .92
        available = max(1, Window.width * popup_width - m.h(28))
        columns = max(2, min(6, int(available // max(1, m.h(140)))))
        rows = (len(options) + columns - 1) // columns
        row_height = 144 if any(order in PENDING_KINDS for _, order in options) else 112
        order_grid = GridLayout(cols=columns, spacing=m.h(8), size_hint_y=None,
                                height=m.h(rows * row_height + (rows - 1) * 8))
        popup = Popup(title=tr("directory." + puzzle), content=content,
                      size_hint=(popup_width, .86),
                      auto_dismiss=True)
        theme_popup(popup, _app().theme)
        for family, order in options:
            label, physical_order = picker_label(family, order)
            mark = MARKS.get(order, str(physical_order))
            pending=isinstance(order,str) and order in PENDING_KINDS
            if pending:label=tr('directory.'+order)
            if len(families) > 1:
                label = tr('directory.' + family) + '\n' + label
            card = (PendingPuzzleCard if pending else HomeCard)(mark, label,
                            image=order_image(family, order),
                            on_click=lambda p=family, n=order: self.select_order(popup, p, n))
            card.puzzle_kind=order
            order_grid.add_widget(card)
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(order_grid)
        content.add_widget(scroll)
        back = UIButton(text=tr('directory.back'), size_hint_y=None, height=m.h(40))
        back.bind(on_release=lambda *_: popup.dismiss())
        content.add_widget(back)
        popup.open()

    def select_order(self, picker, puzzle, order):
        if isinstance(order,str) and order in PENDING_KINDS:
            self.launch_order(puzzle,order)
            return  # Closing the reference returns to this scrolled picker.
        picker.dismiss()
        self.launch_order(puzzle, order)

    def launch_order(self, puzzle, order):
        selected=order if isinstance(order,str) else puzzle
        from cube.bandaged_cube import KINDS as BANDAGE_KINDS
        if selected in BANDAGE_KINDS:
            _app().new_cube_variant(selected,BANDAGE_KINDS[selected])
            self.manager.get_screen('BandagedSixViewScreen')._fresh_request=True
            self.manager.current='BandagedSixViewScreen'
            return
        if selected in ('helicopter','helicopter_14','rua','clover','mf8_bauhinia_minx'):
            _app().new_polyhedral(selected,3)
            self.manager.current='EdgeJumblingInputScreen'
            return
        if isinstance(order,str) and order in PENDING_KINDS:
            self._show_pending(order)
            return
        if isinstance(order,str) and order in BY_KIND and order in ORDERS.get(puzzle,()):
            entry=BY_KIND[order]
            if entry.mechanism=='clover_pyraminx':
                _app().new_clover_pyraminx()
                self.manager.current='CloverPyraminxInputScreen'
            elif entry.mechanism=='butterflower':
                _app().new_butterflower()
                self.manager.current='ButterflowerInputScreen'
            elif entry.mechanism=='flower_copter':
                _app().new_flower_copter()
                self.manager.current='FlowerCopterInputScreen'
            elif entry.mechanism=='hexagram':
                _app().new_hexagram()
                self.manager.current='HexagramInputScreen'
            elif entry.mechanism=='suncube':
                _app().new_suncube()
                self.manager.current='SunCubeInputScreen'
            elif entry.mechanism=='twins':
                _app().new_twins()
                self.manager.current='TwinsInputScreen'
            elif entry.mechanism=='lanlan_comet':
                _app().new_lanlan_comet()
                self.manager.current='LanlanCometInputScreen'
            elif entry.mechanism=='copter':
                _app().new_copter()
                self.manager.current='CopterInputScreen'
            elif entry.mechanism=='football':
                _app().new_polyhedral('football',3)
                self.manager.current='PolyhedralScreen'
            elif entry.mechanism in ('dial_beans','ivy','spherical_minx') or order in POLYHEDRAL_KINDS|DOGIC_KINDS|SIAMESE_KINDS|PRISM_KINDS|{'masterball','rubik_cheese','pyraminx_diamond','cheese_3'}:
                _app().new_polyhedral(order,entry.n)
                self.manager.current='PolyhedralScreen'
            elif entry.mechanism=='extended':
                _app().new_polyhedral(order,entry.n)
                self.manager.current='CuboidSixViewScreen'
            elif entry.mechanism=='shape':
                _app().new_shape_cube(order,entry.n)
                self.manager.current='ShapeCubeScreen'
            elif entry.mechanism=='skewb_shell':
                _app().new_container()
                self.manager.current='ContainerScreen'
            elif entry.mechanism=='mirror_minx':
                _app().new_mirror_minx(entry.n)
                self.manager.current='MirrorMinxScreen'
            elif entry.mechanism=='blanker':
                _app().new_blanker()
                self.manager.current='BlankerScreen'
            else:
                self._show_pending(order,message=tr('expanded.reference_needed'))
            return
        if puzzle in ('mixup_family','tangram_family') and order in ORDERS[puzzle]:
            _app().new_articulated(order)
            self.manager.current='MixupInputScreen' if order.startswith('mixup_') else 'ArticulatedEntryScreen'
            return
        if puzzle == 'penrose_family':
            _app().new_cube_variant(order, CUBE_PATTERN_VARIANTS[order])
            self.manager.current = 'InputScreen'
            return
        if puzzle == 'bandaged_family':
            _app().new_cube_variant(order, CUBE_PATTERN_VARIANTS[order])
            self.manager.current = 'BandagedSixViewScreen'
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
                from ui.screens.polyhedral_screen import _entry_for
                self.manager.current=_entry_for(_app().cube)
            return
        if puzzle == 'circle_family':
            if order not in ORDERS[puzzle]:
                return
            if order == 'circle_2':
                _app().new_polyhedral(order,2)
                self.manager.current='PolyhedralScreen'
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
            if kind in ('void_cube','void_tower','void_minx','mirror_camouflage_3'):
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
            from ui.screens.polyhedral_screen import _entry_for
            self.manager.current = _entry_for(_app().cube)

    def _show_pending(self, puzzle, order=None, message=None):
        if puzzle in PENDING_KINDS:
            return self._show_pending_reference(puzzle)
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

    def _show_pending_reference(self,kind):
        """A catalogue reference leaves the current puzzle and draft intact."""
        existing=getattr(self,'_pending_popup',None)
        if existing is not None and existing._is_open:return existing
        from kivy.uix.image import Image
        content=BoxLayout(orientation='vertical',spacing=m.h(10),padding=m.h(10))
        image=order_image(catalogue_family(kind),kind)
        if image:
            content.add_widget(Image(source=image,fit_mode='contain'))
        else:content.add_widget(Label(text=tr('expanded.pending_short'),color=_app().theme.text_muted))
        status=Label(text=tr('expanded.pending_detail'),size_hint_y=None,height=m.h(66),
                     font_size=m.font(14),halign='center',valign='middle',color=_app().theme.text_muted)
        status.bind(size=lambda w,*_:setattr(w,'text_size',w.size));content.add_widget(status)
        back=UIButton(icon_name='back',size_hint_y=None,height=m.h(44));content.add_widget(back)
        popup=Popup(title=tr('directory.'+kind)+' · '+tr('expanded.pending_short'),content=content,
                    size_hint=(.94,.88),auto_dismiss=True)
        popup.reference_kind=kind
        theme_popup(popup,_app().theme)
        back.bind(on_release=lambda *_:popup.dismiss())
        self._pending_popup=popup
        popup.bind(on_dismiss=lambda *_:setattr(self,'_pending_popup',None))
        popup.open()
        return popup


def _app():
    return App.get_running_app()
