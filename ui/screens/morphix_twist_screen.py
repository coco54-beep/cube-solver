"""专门的粽子 / 镜面拧动界面：选择面 + 顺逆拧动，作用在录入中的整块模型上。

与普通魔方一样，录入页本身不内嵌拧动；本页直接操作来源录入页的 cube
（克隆一份，返回时写回），用真实 3D 动画展示该面的转动。
"""

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.spinner import Spinner

from app.i18n import tr
from cube.polyhedral import dot, cross
from renderer.mastermorphix_view import MastermorphixView
from renderer.turn import decompose_move
from ui.widgets.buttons import UIButton, PrimaryButton
from ui.widgets.layouts import AdaptiveSceneLayout, ResponsiveBoxLayout
from ui.widgets import metrics as m

FACES = ("U", "R", "F", "D", "L", "B")


def _app():
    return App.get_running_app()


def _make_twist_view(cube, **kwargs):
    if getattr(cube, 'puzzle_kind', None) == 'mirror':
        from renderer.mirror_view import MirrorView as base
    else:
        base = MastermorphixView

    class _MorphixTwistView(base):
        def __init__(self, **kw):
            super().__init__(**kw)
            self.on_twist=None
            self.lock_view=True
            self.wide=False
            self._grab=None

        def cancel_touch(self):
            grab=self._grab
            self._grab=None
            if grab is not None:
                grab[0].ungrab(self)
            super().cancel_touch()

        def on_touch_down(self, touch):
            if not self.collide_point(*touch.pos):
                return False
            if (self._anim is not None or self._whole_anim is not None
                    or self._grab is not None or self._touch0 is not None):
                return True
            if not self.lock_view:
                return super().on_touch_down(touch)
            if getattr(touch,'is_mouse_scrolling',False):
                return True
            self._draw_mesh()
            hit=self.pick_surface(*touch.pos)
            if hit is None:
                return True
            self._grab=(touch,tuple(touch.pos),hit)
            touch.grab(self)
            return True

        def on_touch_move(self,touch):
            if self._grab is not None and touch is self._grab[0]:
                return True
            return super().on_touch_move(touch)

        def on_touch_up(self,touch):
            if self._grab is None or touch is not self._grab[0]:
                return super().on_touch_up(touch)
            _,start,hit=self._grab
            self.cancel_touch()
            drag=(touch.x-start[0],touch.y-start[1])
            if sum(v*v for v in drag)>=m.h(18)**2 and self.on_twist:
                spec=self._resolve_twist(hit,drag)
                if spec is not None:
                    self.on_twist(spec)
            return True

        def _resolve_twist(self,hit,drag):
            from renderer.gesture import choose_turn
            from renderer.twist import TwistSpec,_wide_positions
            if self.cube is None or not hasattr(self,'_mm_proj'):
                return None
            pos,point=hit
            right,up,_,_,_,_=self._mm_proj
            whole=self._whole_world
            candidates=[]
            for axis in range(3):
                if self.cube.n%2 and pos[axis]==0 and sum(v!=0 for v in pos)==1:
                    continue
                normal=tuple(1. if i==axis else 0. for i in range(3))
                if whole is not None:
                    normal=whole.transform(*normal)
                velocity=cross(normal,point)
                candidates.append((axis,(dot(velocity,right),dot(velocity,up))))
            chosen=choose_turn(drag,candidates)
            if chosen is None:
                return None
            axis,sign=chosen
            layers=_wide_positions(self.cube.n,axis,pos[axis]) if self.wide else [pos[axis]]
            return TwistSpec(axis,layers,sign)

    return _MorphixTwistView(**kwargs)


class MorphixTwistScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._work = None
        self._source = "MastermorphixScreen"
        self._queue = []
        self._busy = False
        self._history = []
        self._future = []
        self._build()

    def _build(self):
        root = AdaptiveSceneLayout(padding_px=[12, 8, 12, 8], gap_px=8)
        self._root_layout = root

        top = ResponsiveBoxLayout(height_px=44, gap_px=8)
        back = UIButton(icon_name='back', size_hint_x=.16)
        back.bind(on_release=lambda *_: self.back())
        self.title = Label(font_size='20sp')
        done = PrimaryButton(icon_name='done', size_hint_x=.16)
        done.bind(on_release=lambda *_: self.back())
        for item in (back, self.title, done):
            top.add_widget(item)
        root.add_widget(top)

        self.view = MastermorphixView()
        panel = ResponsiveBoxLayout(orientation='vertical', gap_px=7, size_hint_y=None)
        history = ResponsiveBoxLayout(height_px=48, gap_px=8)
        self.btn_undo = UIButton(icon_name='undo')
        self.btn_undo.bind(on_release=lambda *_: self.undo())
        self.btn_redo = UIButton(icon_name='redo')
        self.btn_redo.bind(on_release=lambda *_: self.redo())
        history.add_widget(self.btn_undo)
        history.add_widget(self.btn_redo)
        panel.add_widget(history)
        toggles = ResponsiveBoxLayout(height_px=48, gap_px=8)
        self.btn_lock = UIButton(icon_name='lock')
        self.btn_lock.bind(on_release=lambda *_: self.toggle_lock())
        self.btn_wide = UIButton(icon_name='single')
        self.btn_wide.bind(on_release=lambda *_: self.toggle_wide())
        reset = UIButton(icon_name='reset')
        reset.bind(on_release=lambda *_: self.reset_view())
        for button in (self.btn_lock, self.btn_wide, reset):
            toggles.add_widget(button)
        panel.add_widget(toggles)
        row = ResponsiveBoxLayout(height_px=44, gap_px=6)
        self.face = Spinner(text=FACES[0], values=FACES)
        ccw = UIButton(icon_name='undo', size_hint_x=.28)
        ccw.bind(on_release=lambda *_: self.turn(-1))
        cw = UIButton(icon_name='redo', size_hint_x=.28)
        cw.bind(on_release=lambda *_: self.turn(1))
        for widget in (self.face, ccw, cw):
            row.add_widget(widget)
        panel.add_widget(row)
        self.hint = Label(text=tr('twist.hint_lock_on'), size_hint_y=None, height=m.h(54),
                          font_size='13sp', halign='center', valign='middle')
        self.hint.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        panel.add_widget(self.hint)
        self.panel = panel
        root.set_content(self.view, panel)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        self._source = getattr(_app(), 'morphix_twist_source', 'MastermorphixScreen')
        src = self.manager.get_screen(self._source)
        self._work = src._cube.clone()
        self._recorded = set(src._recorded)
        view = _make_twist_view(self._work, size_hint_y=1)
        view.lock_rotation = True
        view.show_axes = True
        view.on_twist = self.twist
        self._root_layout.replace_scene(view)
        self.view = view
        self.view.set_cube(self._work)
        self.view.recorded = self._recorded
        self._queue = []
        self._busy = False
        self._history = []
        self._future = []
        self.panel.disabled = False
        self._update_controls()
        self.face.text = FACES[0]
        self.retranslate()
        self.refresh_theme()

    def retranslate(self):
        self.title.text = tr('input.twist')
        self.hint.text = tr('poly.twist_hint_on') if getattr(self.view,'lock_view',True) else tr('poly.twist_hint_off')

    def refresh_theme(self):
        self.title.color = _app().theme.text
        self.hint.color = _app().theme.text_muted

    def turn(self, direction):
        face = self.face.text
        self.twist(face if direction > 0 else face + "'")

    def _update_controls(self):
        self.btn_undo.disabled = not self._history
        self.btn_redo.disabled = not self._future
        self.btn_lock.icon_name = 'lock' if self.view.lock_view else 'unlock'
        self.btn_lock.active = self.view.lock_view
        self.btn_wide.icon_name = 'wide' if self.view.wide else 'single'
        self.btn_wide.active = self.view.wide

    def toggle_lock(self):
        if self._busy:
            return
        self.view.cancel_touch()
        self.view.lock_view = not self.view.lock_view
        self.view.lock_rotation = self.view.lock_view
        self._update_controls()
        self.retranslate()

    def toggle_wide(self):
        self.view.cancel_touch()
        self.view.wide = not self.view.wide
        self._update_controls()

    def reset_view(self):
        self.view.cancel_touch()
        self.view.reset_camera()

    def twist(self, move):
        if self._busy or self._work is None:
            return
        from renderer.twist import TwistSpec
        if isinstance(move, str):
            step = decompose_move(move, self._work.n)[0]
            move = TwistSpec(step.axis, step.layers, 1 if step.angle>0 else -1)
        self._history.append(move)
        self._future.clear()
        self._animate(move)

    def undo(self):
        if self._busy or not self._history:
            return
        from renderer.twist import TwistSpec
        move=self._history.pop()
        self._future.append(move)
        self._animate(TwistSpec(move.axis, move.layer_positions, -move.sign))

    def redo(self):
        if self._busy or not self._future:
            return
        move=self._future.pop()
        self._history.append(move)
        self._animate(move)

    def _animate(self, move):
        self.view.cancel_touch()
        self._busy=True
        self.panel.disabled=True
        self._update_controls()
        # Keep odd-order fixed centres out of a middle-slice animation too.
        def done():
            from renderer.twist import ROT_PLUS
            def destination(pos):
                if pos[move.axis] not in move.layer_positions or (
                    self._work.n%2 and pos[move.axis]==0 and sum(v!=0 for v in pos)==1):
                    return pos
                for _ in range(move.sign%4):
                    pos=ROT_PLUS[move.axis](*pos)
                return pos
            self._recorded={destination(pos) for pos in self._recorded}
            self._work.turn_layer(move.axis, move.layer_positions, move.sign)
            self.view.set_cube(self._work)
            self.view.recorded=self._recorded
            self._busy=False
            self.panel.disabled=False
            self._update_controls()
            _app().solve_result=None
        self.view.start_turn(move.axis, move.layer_positions[0], 90*move.sign, .4,
                             on_done=done, layer_positions=move.layer_positions,
                             include_fixed_centers=False)

    def back(self):
        if self._busy:
            return
        try:
            src = self.manager.get_screen(self._source)
            src._cube = self._work
            src._recorded = set(self._recorded)
        except Exception:
            pass
        self.manager.current = self._source

    def on_leave(self, *args):
        self.view.cancel_touch()
        self.view._cancel_animation()
        self._busy = False
        self.panel.disabled = False

    def reset_interaction(self):
        self.view.cancel_touch()
