"""拧魔方页：三维自由视角下，直接拖动魔方来拧动某一层。

模式：
- 卡视角 开：手指在魔方上拖动 = 拧动一层。以手指接触的"小面"为动点：
  转动作用在哪一层由该小面所属的块决定（小面所在层），
  绕哪根轴 / 顺逆方向由拖动方向决定。视图不随手指旋转。
- 卡视角 关：拖动旋转视角、滚轮/双指缩放（CubeView 默认行为）。
- 还原视角：回到默认的三维观察角度。

每次拧动完成后立即把新的颜色分布回写到录入页（input_screen._data），
未填色的小面（空串）会跟着一起移动，不影响拧动，也不做合法性校验。
"""

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from ui.widgets.buttons import UIButton
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from app.constants import FACES
from app.i18n import tr
from renderer.cube_view import CubeView
from renderer.twist import resolve_twist, apply_layer_turn
from cube.conversion import cubies_to_facelets
from cube.cube2 import Cube2
from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.cube5 import Cube5
from ui.screens.input_screen import (
    PrimaryButton, _build_partial_cube,
)


def _app():
    from kivy.app import App
    return App.get_running_app()


class _TwistCubeView(CubeView):
    """拧魔方视图：根据 lock_view 决定拖动是拧层还是转视角。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lock_view = True       # True=拧层，False=转视角
        self.on_twist = None
        self._press = None
        self._touch0 = None
        self._grab_pick = None      # 本次按下接触的小面 (cubie_pos, face_name)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if getattr(touch, "is_mouse_scrolling", False):
            if self.lock_view:
                return True
            return super().on_touch_down(touch)
        if self.lock_view:
            if self.on_twist is not None:
                # 拧层模式：记录按下点（接触的小面），不抓取相机旋转。
                self._touch0 = touch
                self._press = touch.pos
                self._grab_pick = self.pick_facelet(*touch.pos)
                try:
                    touch.grab(self)
                except Exception:
                    pass
                return True
            return super().on_touch_down(touch)
        # 自由视角：走 CubeView 默认（抓触摸 + 拖动旋转）。
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.lock_view:
            if touch is not self._touch0:
                return super().on_touch_move(touch)
            # 拧层模式不旋转视角，仅跟踪拖动。
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.lock_view:
            if touch is not self._touch0:
                return super().on_touch_up(touch)
            try:
                touch.ungrab(self)
            except Exception:
                pass
            press = self._press
            self._touch0 = None
            self._press = None
            grab_pick = self._grab_pick
            self._grab_pick = None
            if press is not None and self.on_twist is not None:
                dx = touch.x - press[0]
                dy = touch.y - press[1]
                if dx * dx + dy * dy > 18 * 18:
                    self._resolve_and_twist(press, (dx, dy), grab_pick)
            return True
        return super().on_touch_up(touch)

    def _resolve_and_twist(self, press, drag, grab_pick=None):
        proj = self._last_proj
        if proj is None:
            return
        basis = proj["basis"]
        grab_pos = grab_face = None
        if grab_pick is not None:
            grab_pos, grab_face = grab_pick
        spec = resolve_twist(
            self._n(),
            basis,
            proj["pixel_scale"],
            proj["center_x"],
            proj["center_y"],
            proj["widget_center_x"],
            proj["widget_center_y"],
            drag,
            press,
            wide=self._wide,
            grab_pos=grab_pos,
            grab_face=grab_face,
        )
        if spec is not None:
            self.on_twist(spec)

    def _n(self):
        return _app().n


class TwistScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._work = None
        self._busy = False
        self._wide = False
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=8, padding=[8, 6, 8, 8])

        # 顶栏
        top = BoxLayout(size_hint_y=None, height=46, spacing=8)
        back = UIButton(text=tr("input.back"), size_hint_x=0.22)
        back.bind(on_release=lambda *a: self.go_back())
        self.title = Label(text=tr("input.twist"), size_hint_x=0.56, halign="center",
                           font_size="20sp", bold=True)
        done = PrimaryButton(text=tr("twist.done"), size_hint_x=0.22)
        done.bind(on_release=lambda *a: self.go_back())
        top.add_widget(back)
        top.add_widget(self.title)
        top.add_widget(done)
        root.add_widget(top)

        # 3D 视图
        self.view = _TwistCubeView(size_hint=(1.0, 1.0))
        self.view.on_twist = self._twist
        self.view._wide = False
        root.add_widget(self.view)

        # 控制区
        ctl = BoxLayout(size_hint_y=None, height=52, spacing=8)
        self.btn_lock = UIButton(text=tr("twist.lock_on"), font_size="15sp", size_hint_x=0.3)
        self.btn_lock.bind(on_release=lambda *a: self.toggle_lock())
        self.btn_wide = UIButton(text=tr("twist.wide_off"), font_size="15sp", size_hint_x=0.3)
        self.btn_wide.bind(on_release=lambda *a: self.toggle_wide())
        self.btn_reset = UIButton(text=tr("playback.reset_view"), font_size="15sp", size_hint_x=0.4)
        self.btn_reset.bind(on_release=lambda *a: self.view.reset_camera())
        ctl.add_widget(self.btn_lock)
        ctl.add_widget(self.btn_wide)
        ctl.add_widget(self.btn_reset)
        root.add_widget(ctl)

        # 提示
        self.msg = Label(text="", size_hint_y=None, height=34,
                         color=(0.7, 0.85, 0.7, 1), halign="center",
                         font_size="14sp")
        root.add_widget(self.msg)

        self.add_widget(root)

    def retranslate(self):
        if not hasattr(self, "title"):
            return
        self.title.text = tr("input.twist")
        self.btn_reset.text = tr("playback.reset_view")
        self._update_toggle_texts()
        self.msg.text = tr("twist.hint_lock_on") if self.view.lock_view else tr("twist.hint_lock_off")

    def _update_toggle_texts(self):
        self.btn_lock.text = tr("twist.lock_on") if self.view.lock_view else tr("twist.lock_off")
        self.btn_wide.text = tr("twist.wide_on") if self._wide else tr("twist.wide_off")

    # ---- 进入 / 初始化 ----
    def on_enter(self):
        n = _app().n
        input_screen = self._input_screen()
        facelets = input_screen.collect_facelets()
        cube = _build_partial_cube(facelets, n)
        if cube is None:
            cube = _solved_for(n)
        self._work = cube
        self.view.lock_view = True
        self._update_toggle_texts()
        self.view.reset_camera()
        self._refresh_view()
        self.msg.text = tr("twist.hint_lock_on")

    def _input_screen(self):
        try:
            return self.manager.get_screen("InputScreen")
        except Exception:
            return None

    def _refresh_view(self):
        self.view.set_cube(self._work)

    # ---- 交互 ----
    def toggle_lock(self):
        self.view.lock_view = not self.view.lock_view
        self._update_toggle_texts()
        if self.view.lock_view:
            self.msg.text = tr("twist.hint_lock_on")
        else:
            self.msg.text = tr("twist.hint_lock_off")

    def toggle_wide(self):
        self._wide = not self._wide
        self.view._wide = self._wide
        self._update_toggle_texts()
        self.msg.text = tr("twist.hint_wide")

    def _twist(self, spec):
        if self._busy:
            return
        self._busy = True
        angle = 90 * spec.sign
        dur = 0.4 * abs(angle) / 90.0
        self.view.start_turn(
            spec.axis,
            spec.layer_positions[0],
            angle,
            dur,
            on_done=lambda: self._after_twist(spec),
            layer_positions=spec.layer_positions,
            include_fixed_centers=True,
        )

    def _after_twist(self, spec):
        apply_layer_turn(self._work.cubies, spec.axis,
                         spec.layer_positions, spec.sign)
        self.view.set_cube(self._work)
        self._write_back()
        self._busy = False

    def _write_back(self):
        input_screen = self._input_screen()
        if input_screen is None:
            return
        n = _app().n
        facelets = cubies_to_facelets(self._work.cubies, n)
        clean = {}
        for f in FACES:
            grid = facelets.get(f, [])
            clean[f] = [[(g if g else "") for g in row] for row in grid]
        input_screen.set_facelets(clean)
        # 同步刷新应用记录的布局，避免回到录入页时 on_enter
        # 用拧动前的旧 facelets_input 覆盖刚拧好的分布。
        _app().facelets_input = clean

    def go_back(self):
        self._write_back()
        self.manager.current = "InputScreen"


def _solved_for(n):
    if n == 2:
        return Cube2.solved()
    if n == 4:
        return Cube4.solved()
    if n == 5:
        return Cube5.solved()
    return Cube3.solved()
