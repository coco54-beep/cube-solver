"""演示目录页：按阶数列出教学案例（缩略图 + 文字），点击跳转到对应演示。

缩略图用 CubeView 离线渲染案例初始态为 PNG 并缓存，便于快速根据魔方状态
选择对应步骤。
"""

import os
import hashlib

from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.uix.popup import Popup
from ui.widgets.buttons import UIButton, PrimaryButton
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from demo.cases import localized
from app.i18n import tr
from renderer.mastermorphix_mesh import STYLE_VERSION
from app.constants import COLOR_INFO
from ui.screens.demo_screen import (_changed_homes, _build_case_cube, _steps_for,
                                   _mode_title, _demo_view_for, _set_demo_cube)
from ui.widgets import metrics as m
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets.dialogs import theme_popup
from demo.solutions import make_scrambled_demo, verified_solution_lessons, state_signature
from services.solve_service import SolveService

DEMO_REVISION='accuracy-2026-10-12-v2'


def source_screen(mode):
    kind=mode[0] if isinstance(mode,tuple) else mode
    return {'mastermorphix':'MastermorphixScreen','mirror':'MirrorScreen',
            'axis':'ShapeCubeScreen','pandora':'ShapeCubeScreen',
            'windmill':'ShapeCubeScreen','fisher':'ShapeCubeScreen',
            'square1':'Square1Screen','mirror_tower':'MirrorTowerScreen'}.get(
                kind,'PolyhedralScreen' if isinstance(mode,tuple) else 'InputScreen')


def _num(n):
    return ["一", "二", "三", "四", "五", "六", "七", "八", "九"][n]


def _mode_menu_title(n):
    if isinstance(n, tuple):
        return _mode_title(n)
    return tr(f"demo.mode.menu.{n}")


_MODE_TITLE = {2: "demo.mode.menu.2", 3: "demo.mode.menu.3",
               4: "demo.mode.menu.4", 5: "demo.mode.menu.5",
               "mastermorphix": "demo.mode.menu.mastermorphix"}


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


def render_thumb(case, n, size=140):
    """渲染案例初始态为 PNG，缓存后返回路径；失败返回 None。"""
    cube = _build_case_cube(n, case)
    from app.prefs import get
    identity=repr((DEMO_REVISION,n,case['moves'],state_signature(cube),
                   getattr(cube,'palette',None),COLOR_INFO,
                   get('poly_palette_'+n[0],None) if isinstance(n,tuple) else None,
                   STYLE_VERSION))
    key=hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]
    path=os.path.join(_thumbs_dir(),'demo_'+key+'.png')
    if os.path.exists(path):
        return path
    try:
        v = _demo_view_for(cube, size_hint=(None, None), size=(size, size))
        highlight=None if 'initial' in case or isinstance(n,tuple) or n=='mastermorphix' else _changed_homes(cube)
        _set_demo_cube(v, cube,highlight)
        v.reset_camera()
        if hasattr(v, '_draw'):
            v._draw()
            if v._fbo is not None:
                v._fbo.draw()
        else:
            v._draw_mesh()
            if getattr(v, '_surface_fbo', None) is not None:
                v._surface_fbo.draw()
        v.export_to_png(path)
        return path
    except Exception:
        from kivy.logger import Logger
        Logger.exception('Demo: thumbnail rendering failed')
        return None


class DemoMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = 3
        self._solution_steps=None
        self._job=None
        self._service=SolveService()
        self._solve_popup=None
        self.build_ui()

    def build_ui(self):
        root = ResponsiveBoxLayout(orientation="vertical", gap_px=4,
                                   padding_px=[8, 6, 8, 8])

        top = ResponsiveBoxLayout(height_px=48, gap_px=6)
        self.btn_back = UIButton(text="", icon_name="back", size_hint_x=0.22)
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
        if self.mode!=n:
            self._solution_steps=None
        self.mode = n
        self.lbl_title.text = _mode_menu_title(n)
        self._rebuild()

    def retranslate(self):
        if not hasattr(self, "lbl_title"):
            return
        self.lbl_title.text = _mode_menu_title(self.mode)
        self._rebuild()

    def _rebuild(self):
        self.list.clear_widgets()
        actions=ResponsiveBoxLayout(height_px=52,gap_px=8)
        for key,callback in (('demo.complete',self.start_complete_demo),('demo.my_input',self.solve_current_input)):
            button=PrimaryButton(text=tr(key))
            button.bind(on_release=lambda *_,fn=callback:fn())
            actions.add_widget(button)
        self.list.add_widget(actions)
        if self._solution_steps:
            self._add_steps(self._solution_steps)
        steps = _steps_for(self.mode)
        self._add_steps(steps)

    def _add_steps(self,steps):
        for si, step in enumerate(steps):
            head = Label(text=tr("demo.menu_step", cn=_num(si), n=si + 1,
                                 title=tr(localized(step['title']))),
                         font_size="16sp",
                         bold=True, halign="left", valign="middle",
                         color=_app().theme.text)
            _autofit(head)
            self.list.add_widget(head)
            for ci, case in enumerate(step["cases"]):
                self.list.add_widget(self._row(si, ci, case,steps))

    def _row(self, si, ci, case,steps=None):
        row = BoxLayout(size_hint_y=None, height=m.h(120), spacing=8, padding=[0, 4, 0, 4])
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
        name = Label(text=tr(localized(case["name"])), font_size="16sp", bold=True,
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
            row.height = max(m.h(120), info.height + 8)

        for w in (name, formula, tip):
            w.bind(texture_size=_sync)
        _sync()
        # 整行可点击
        row.bind(on_touch_down=self._row_press)
        row.bind(on_touch_up=lambda inst, touch, s=si, c=ci: self._row_touch(
            inst, touch, s, c,steps))
        row.add_widget(info)
        return row

    def _row_press(self, row, touch):
        if not getattr(touch, 'is_mouse_scrolling', False) and row.collide_point(*touch.pos):
            touch.ud[('demo-row', id(self))] = (row, touch.pos)
        return False

    def _row_touch(self, row, touch, si, ci,steps=None):
        pressed = touch.ud.get(('demo-row', id(self)))
        if (pressed and pressed[0] is row and row.collide_point(*touch.pos)
                and sum((a-b)**2 for a,b in zip(pressed[1],touch.pos)) <= m.h(12)**2):
            touch.ud.pop(('demo-row', id(self)), None)
            self.open_case(si, ci,steps)
            return True
        return False

    def refresh_theme(self):
        """主题切换后按当前主题色重建列表。"""
        self.lbl_title.color = _app().theme.text
        if getattr(self, "list", None):
            self._rebuild()

    def open_case(self, si, ci,steps=None):
        demo = self.manager.get_screen("DemoScreen")
        demo.enter_case(self.mode, si, ci,steps)
        self.manager.current = "DemoScreen"

    def start_complete_demo(self):
        if self._job is not None:
            return
        job=object()
        self._job=job
        message=Label(text=tr('demo.preparing_complete'),halign='center',valign='middle')
        message.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        content=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        content.add_widget(message)
        cancel=UIButton(text=tr('poly.cancel'),height=m.h(44),size_hint_y=None)
        content.add_widget(cancel)
        popup=Popup(title=tr('demo.complete'),content=content,size_hint=(.86,.34),auto_dismiss=False)
        theme_popup(popup,_app().theme)
        self._solve_popup=popup
        cancel.bind(on_release=lambda *_:self._cancel_complete())
        popup.open()
        try:
            initial=make_scrambled_demo(self.mode)
        except Exception as exc:
            self._finish_complete(job,None,str(exc))
            return
        def progress(payload):
            def update(_dt):
                if self._job is job:
                    message.text=tr('demo.preparing_complete')
                    if 'done' in payload and payload['done']>=0:
                        message.text+='\n'+tr('poly.stage',done=payload['done'],total=payload['total'])
            Clock.schedule_once(update,0)
        def done(result):
            try:
                steps=verified_solution_lessons(initial,result)
                error=None
            except Exception as exc:
                steps=None
                error=str(exc)
            Clock.schedule_once(lambda _dt:self._finish_complete(job,steps,error),0)
        self._service.start(initial.clone(),done,progress)

    def _finish_complete(self,job,steps,error):
        if self._job is not job:
            return
        self._job=None
        if self._solve_popup:
            self._solve_popup.dismiss()
            self._solve_popup=None
        if error:
            label=Label(text=tr('demo.complete_failed',detail=error),halign='center',valign='middle')
            label.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
            popup=Popup(title=tr('poly.error.solve_title'),content=label,size_hint=(.86,.4))
            theme_popup(popup,_app().theme)
            popup.open()
            return
        self._solution_steps=steps
        self._rebuild()
        self.open_case(0,0,steps)

    def _cancel_complete(self):
        self._job=None
        self._service.cancel()
        if self._solve_popup:
            self._solve_popup.dismiss()
            self._solve_popup=None

    def solve_current_input(self):
        source=self.manager.get_screen(source_screen(self.mode))
        self.manager.current=source.name
        if source.name=='Square1Screen' and source._playback:
            source._return_to_input()
        callback=getattr(source,'start_solve',None) or source.solve
        Clock.schedule_once(lambda _dt:callback(),0)

    def on_leave(self,*args):
        if self._job is not None:
            self._cancel_complete()

    def go_home(self):
        self.manager.current=source_screen(self.mode)


def _app():
    from kivy.app import App
    return App.get_running_app()
