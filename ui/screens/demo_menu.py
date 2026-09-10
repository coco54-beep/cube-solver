"""演示目录页：按阶数列出教学案例（缩略图 + 文字），点击跳转到对应演示。

缩略图用 CubeView 离线渲染案例初始态为 PNG 并缓存，便于快速根据魔方状态
选择对应步骤。
"""

import os

from kivy.uix.boxlayout import BoxLayout
from ui.widgets.buttons import UIButton
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from cube.cube2 import Cube2
from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.cube5 import Cube5
from demo.cases import CASE_2X2, CASE_3X3, CASE_4X4, CASE_5X5, build_before, localized
from app.i18n import tr
from renderer.cube_view import CubeView
from ui.screens.demo_screen import _changed_homes


def _num(n):
    return ["一", "二", "三", "四", "五", "六", "七", "八", "九"][n]


def _mode_menu_title(n):
    return tr(f"demo.mode.menu.{n}")


_MODE_TITLE = {2: "demo.mode.menu.2", 3: "demo.mode.menu.3",
               4: "demo.mode.menu.4", 5: "demo.mode.menu.5"}
_MODE_STEPS = {2: CASE_2X2, 3: CASE_3X3, 4: CASE_4X4, 5: CASE_5X5}


def _autofit(lbl, pad=1):
    """文字自动换行并自动增高，防止长文本超出盒子与相邻控件重叠。"""
    lbl.size_hint_y = None
    lbl.bind(width=lambda w, s: setattr(w, "text_size", (s, None)) if s else None)

    def _h(w, tex):
        if tex[0]:
            w.height = tex[1] + pad

    lbl.bind(texture_size=_h)


def _thumbs_dir():
    d = os.path.join(_app().user_data_dir, "thumbs")
    os.makedirs(d, exist_ok=True)
    return d


def _slug(name):
    safe = []
    for ch in name:
        safe.append(ch if ch.isalnum() else "_")
    return "".join(safe)


def render_thumb(case, n, size=140):
    """渲染案例初始态为 PNG，缓存后返回路径；失败返回 None。"""
    path = os.path.join(_thumbs_dir(), f"{n}_{_slug(localized(case['name'], 'zh'))}.png")
    if os.path.exists(path):
        return path
    cls = {2: Cube2, 3: Cube3, 4: Cube4, 5: Cube5}[n]
    cube = build_before(cls.solved, case["moves"])
    hl = _changed_homes(cube)
    try:
        v = CubeView(size=(size, size))
        v.set_cube(cube, highlight=hl)
        v._draw_mesh()
        v.export_to_png(path)
        return path
    except Exception:
        return None


class DemoMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = 3
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=4, padding=[8, 6, 8, 8])

        top = BoxLayout(size_hint_y=None, height=46, spacing=6)
        self.btn_back = UIButton(text=tr("input.back"), size_hint_x=0.22)
        self.btn_back.bind(on_release=lambda *a: self.go_home())
        self.lbl_title = Label(text=tr(_MODE_TITLE[3]), size_hint_x=0.78, halign="center",
                               bold=True, font_size="20sp")
        top.add_widget(self.btn_back)
        top.add_widget(self.lbl_title)
        root.add_widget(top)

        self.scroll = ScrollView()
        self.list = BoxLayout(orientation="vertical", spacing=6,
                              size_hint_y=None, padding=[0, 4, 0, 4])
        self.list.bind(minimum_height=self.list.setter("height"))
        self.scroll.add_widget(self.list)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def set_mode(self, n):
        self.mode = n
        self.lbl_title.text = tr(_MODE_TITLE[n])
        self._rebuild()

    def retranslate(self):
        if not hasattr(self, "lbl_title"):
            return
        self.lbl_title.text = tr(_MODE_TITLE[self.mode])
        self._rebuild()

    def _rebuild(self):
        self.list.clear_widgets()
        steps = _MODE_STEPS[self.mode]
        for si, step in enumerate(steps):
            head = Label(text=tr("demo.menu_step", cn=_num(si), n=si + 1,
                                 title=localized(step['title'])),
                         font_size="16sp",
                         bold=True, halign="left", valign="middle",
                         color=_app().theme.text)
            _autofit(head)
            self.list.add_widget(head)
            for ci, case in enumerate(step["cases"]):
                self.list.add_widget(self._row(si, ci, case))

    def _row(self, si, ci, case):
        row = BoxLayout(size_hint_y=None, height=120, spacing=8, padding=[0, 4, 0, 4])
        # 缩略图
        thumb_png = render_thumb(case, self.mode)
        if thumb_png:
            img = Image(source=thumb_png, size_hint=(None, None),
                        size=(120, 120), keep_ratio=True)
        else:
            img = Label(text=tr("demo.no_image"), size_hint=(None, None), size=(120, 120))
        row.add_widget(img)
        # 文字列：自动换行 + 自动增高，行高随内容联动，杜绝重叠
        info = BoxLayout(orientation="vertical", spacing=2)
        name = Label(text=localized(case["name"]), font_size="16sp", bold=True,
                     halign="left", valign="middle")
        formula = Label(text=localized(case["text"]), font_size="13sp", halign="left",
                        valign="middle", color=_app().theme.text_muted)
        tip = Label(text=localized(case["tip"]), font_size="13sp", halign="left",
                    valign="middle", color=_app().theme.text_faint)
        for w in (name, formula, tip):
            _autofit(w)
            info.add_widget(w)

        def _sync(*_a):
            info.height = name.height + formula.height + tip.height + 2 * 2
            row.height = max(120, info.height + 8)

        for w in (name, formula, tip):
            w.bind(texture_size=_sync)
        _sync()
        # 整行可点击
        row.bind(on_touch_down=lambda inst, touch, s=si, c=ci: self._row_touch(
            inst, touch, s, c))
        row.add_widget(info)
        return row

    def _row_touch(self, row, touch, si, ci):
        if row.collide_point(*touch.pos):
            self.open_case(si, ci)
            return True
        return False

    def refresh_theme(self):
        """主题切换后按当前主题色重建列表。"""
        self.lbl_title.color = _app().theme.text
        if getattr(self, "list", None):
            self._rebuild()

    def open_case(self, si, ci):
        demo = self.manager.get_screen("DemoScreen")
        demo.enter_case(self.mode, si, ci)
        self.manager.current = "DemoScreen"

    def go_home(self):
        self.manager.current = "InputScreen"


def _app():
    from kivy.app import App
    return App.get_running_app()
