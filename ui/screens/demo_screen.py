"""播放公式教学案例，以及从独立打乱状态求解得到的完整还原和阶段演示。"""

from kivy.uix.boxlayout import BoxLayout
from ui.widgets.buttons import UIButton, PrimaryButton, ArrowButton
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from cube.mastermorphix import MastermorphixCube
from demo.cases import (
    CASE_2X2, CASE_3X3, CASE_4X4, CASE_5X5,
    localized,
)
from demo.mastermorphix_cases import CASE_MASTERMORPHIX
from app.i18n import tr
from renderer.cube_view import CubeView
from renderer.mastermorphix_view import MastermorphixView
from renderer.turn import decompose_move
from cube.mirror import MirrorCube
from cube.polyhedral import PolyhedralPuzzle
from renderer.polyhedral_view import PolyhedralView
from demo.irregular_cases import lessons, token
from demo.solutions import build_example, inverse_demo_move
from demo.cases import TEACHING_COLORS
from renderer.camera_follow import follow_turn,layer_target,polyhedral_target,square1_target,cancel_follow,reset_camera_view
from ui.widgets.camera_follow import CameraFollowControl
from ui.widgets import metrics as m
from ui.widgets.layouts import ResponsiveBoxLayout, AdaptiveSceneLayout


def _theme():
    from kivy.app import App
    return App.get_running_app().theme


def _mode_title(n):
    if n == "cfop":
        return tr("formula.title")
    if isinstance(n, tuple):
        if n[0] in ('blossom','ivy'):
            return tr('directory.'+n[0])
        if n[0]=='dino':
            kind='dinosaur' if n[1]==2 else 'lattice'
            return tr('directory.'+kind)+' · '+tr('directory.order',order=n[1])
        return tr('directory.' + n[0]) + ' · ' + tr('directory.order', order=n[1])
    return tr(f"demo.mode.title.{n}")


DEMO_MODES = (2, 3, 4, 5, "mastermorphix")


def _steps_for(n):
    if n == "cfop":
        from demo.cfop_cases import CFOP_CASES
        return CFOP_CASES
    if isinstance(n, tuple):
        return lessons(*n)
    return {2: CASE_2X2, 3: CASE_3X3, 4: CASE_4X4, 5: CASE_5X5,
            "mastermorphix": CASE_MASTERMORPHIX}[n]


def _build_case_cube(mode, case):
    return build_example(mode,case)


def _inverse_demo_move(move, cube):
    return inverse_demo_move(move,cube)


def _demo_view_class(cube):
    if isinstance(cube,PolyhedralPuzzle):
        return PolyhedralView
    from cube.square1 import Square1Cube
    if isinstance(cube,Square1Cube):
        from renderer.square1_view import Square1View
        return Square1View
    from cube.mirror_tower import MirrorTowerCube
    if isinstance(cube,MirrorTowerCube):
        from renderer.mirror_tower_view import MirrorTowerView
        return MirrorTowerView
    kind=getattr(cube,'puzzle_kind',None)
    if kind in ('axis','pandora','windmill','fisher'):
        from renderer.shape_cube_view import AxisView,PandoraView,WindmillView,FisherView
        return {'axis':AxisView,'pandora':PandoraView,'windmill':WindmillView,'fisher':FisherView}[kind]
    if isinstance(cube,MirrorCube):
        from renderer.mastermorphix_view import cube_view_class_for
        return cube_view_class_for(cube)
    return MastermorphixView if isinstance(cube,MastermorphixCube) else CubeView


def _demo_view_for(cube, **kwargs):
    return _demo_view_class(cube)(**kwargs)


def _set_demo_cube(view, cube, highlight=None):
    if isinstance(cube, PolyhedralPuzzle):
        view.set_cube(cube)
        from app.prefs import get
        palette = get('poly_palette_' + cube.puzzle_kind, None)
        if (isinstance(palette, list) and len(palette) == len(cube.geometry.spec.normals)
                and all(isinstance(c, list) and len(c) == 4
                        and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in c)
                        for c in palette)):
            view.palette = tuple(tuple(c) for c in palette)
    elif cube.__class__.__name__ in ('Square1Cube','MirrorTowerCube'):
        view.set_cube(cube)
    else:
        view.set_cube(cube, highlight=highlight)


def _autofit(lbl, pad=1):
    """让 Label 随文本自动换行并自动增高，杜绝文字溢出/重叠。

    宽度 -> text_size 换行；texture 高度 -> Label 高度。保证文字永远不超出
    自身盒子（Kivy 不裁剪，固定高度 + 长文本 wrap 会绘制到相邻控件上）。
    """
    lbl.size_hint_y = None
    lbl.bind(width=lambda w, s: setattr(w, "text_size", (s, None)) if s else None)

    def _h(w, tex):
        if tex[0]:
            w.height = tex[1] + pad

    lbl.bind(texture_size=_h)


class DemoScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = 3
        self._steps = CASE_3X3
        self._si = 0
        self._ci = 0
        self._work = None
        self._initial = None
        self._moves = []
        self._move_index = 0
        self._pending_index = None
        self._pending_move = None
        self._queue = []
        self._busy = False
        self._playing = False
        self.build_ui()

    def build_ui(self):
        root = AdaptiveSceneLayout(gap_px=4,
                                   padding_px=[8, 6, 8, 8])
        self._root_layout = root

        # 顶栏：返回目录 + 标题 + 播放
        top = ResponsiveBoxLayout(height_px=48, gap_px=6)
        self.btn_back = UIButton(text="", icon_name="back", size_hint_x=0.2)
        self.btn_back.bind(on_release=lambda *a: self.go_menu())
        self.lbl_mode = Label(text=_mode_title(3), size_hint_x=0.45, halign="center",
                              bold=True, font_size="18sp")
        top.add_widget(self.btn_back)
        top.add_widget(self.lbl_mode)
        top.add_widget(Widget(size_hint_x=self.btn_back.size_hint_x))
        root.add_widget(top)

        # 3D 视图
        self.view = CubeView(size_hint_y=0.5)
        panel = ResponsiveBoxLayout(orientation="vertical", gap_px=8)

        # 信息区：文字随内容自动增高，放入 ScrollView，长文本可滚动而不重叠。
        sv = ScrollView(size_hint_y=0.5)
        info = BoxLayout(orientation="vertical", size_hint_y=None, spacing=3,
                         padding=[2, 0, 2, 0])
        info.bind(minimum_height=info.setter("height"))
        self.lbl_title = Label(text="", font_size="17sp", bold=True, halign="left",
                               valign="middle", color=_theme().text)
        self.lbl_desc = Label(text="", font_size="13sp", halign="left", valign="top",
                              color=_theme().text_muted)
        self.lbl_case = Label(text="", font_size="15sp", halign="left", valign="middle",
                              color=_theme().text)
        self.lbl_text = Label(text="", font_size="18sp", halign="center",
                              valign="middle", bold=True)
        self.lbl_tip = Label(text="", font_size="14sp", halign="center",
                             valign="middle", color=_theme().text_muted)
        self.lbl_progress = Label(text="", font_size="14sp", halign="center",
                                  valign="middle", color=_theme().text_muted)
        for w in (self.lbl_title, self.lbl_desc, self.lbl_case,
                  self.lbl_text, self.lbl_tip, self.lbl_progress):
            _autofit(w)
            info.add_widget(w)
        sv.add_widget(info)
        panel.add_widget(sv)

        # 控制区（两行：播放步进 + 视角）
        control = ResponsiveBoxLayout(height_px=52, gap_px=8,
                                      padding_px=[28, 0, 28, 0])
        self.btn_start = UIButton(text="", icon_name="first")
        self.btn_start.bind(on_release=lambda *a: self.to_start())
        self.btn_prev = ArrowButton(direction="left")
        self.btn_prev.bind(on_release=lambda *a: self.prev_move())
        self.btn_play = PrimaryButton(text="", icon_name="solve")
        self.btn_play.bind(on_release=lambda *a: self.play())
        self.btn_next = ArrowButton(direction="right")
        self.btn_next.bind(on_release=lambda *a: self.next_move())
        self.btn_reset = UIButton(text="", icon_name="reset")
        self.btn_reset.bind(on_release=lambda *a: reset_camera_view(self.view) if not self._busy else None)
        for b in (self.btn_start, self.btn_prev, self.btn_play,
                  self.btn_next, self.btn_reset):
            control.add_widget(b)
        panel.add_widget(control)
        self.follow_control=CameraFollowControl()
        self.follow_control.bind_view(self.view)
        panel.add_widget(self.follow_control)
        root.set_content(self.view, panel, portrait_fraction=.5)

        self.add_widget(root)
        self._update_controls()

    def retranslate(self):
        if not hasattr(self, "lbl_mode"):
            return
        self.lbl_mode.text = _mode_title(self.mode)
        self.follow_control.retranslate()
        self._refresh_case_text()
        self._update_controls()

    def refresh_theme(self):
        """主题切换后刷新信息区文字颜色。"""
        t = _theme()
        self.lbl_mode.color = t.text
        self.lbl_title.color = t.text
        self.lbl_desc.color = t.text_muted
        self.lbl_case.color = t.text
        self.lbl_tip.color = t.text_muted
        self.lbl_progress.color = t.text_muted

    # ---- 模式 / 导航 ----
    def enter_case(self, mode, si, ci, steps=None, return_screen=None):
        """从目录跳到指定案例。"""
        self.mode = mode
        self._return_screen = return_screen
        self._steps = steps if steps is not None else _steps_for(mode)
        self.lbl_mode.text = _mode_title(mode)
        self._si = si
        self._ci = ci
        self._show_case()
        if 'camera' not in self._case() and (self.mode in ("cfop", "mastermorphix") or isinstance(self.mode, tuple)):
            self.view.reset_camera()

    def toggle_mode(self):
        index = DEMO_MODES.index(self.mode) if self.mode in DEMO_MODES else -1
        self.mode = DEMO_MODES[(index + 1) % len(DEMO_MODES)]
        self._steps = _steps_for(self.mode)
        self.lbl_mode.text = _mode_title(self.mode)
        self._si = 0
        self._ci = 0
        self._show_case()

    def _step(self):
        return self._steps[self._si]

    def _case(self):
        return self._step()["cases"][self._ci]

    def _show_case(self):
        self._stop()
        case = self._case()
        cube = _build_case_cube(self.mode, case)
        expected_view=_demo_view_class(cube)
        if type(self.view) is not expected_view:
            self.view = _demo_view_for(cube, size_hint_y=0.5)
            self._root_layout.replace_scene(self.view)
        if isinstance(cube, MastermorphixCube):
            self.view.show_axes = True
        self.follow_control.bind_view(self.view)
        self._work = cube
        self._initial = cube.clone()
        self._moves = list(case["moves"])
        self._move_index = 0
        # 聚焦：只给被移动/参与公式的块上色，其余灰色
        self._highlight = None if "initial" in case or case.get('show_all') or self.mode == "mastermorphix" or isinstance(self.mode, tuple) else _changed_homes(cube)
        _set_demo_cube(self.view, cube, self._highlight)
        if hasattr(self.view,'set_tutorial_targets'):
            self.view.set_tutorial_targets(case.get('tutorial_targets',{}))
        if 'camera' in case:
            self.view.yaw, self.view.pitch, self.view.roll = case['camera']
            self.view.refresh()
        self._refresh_case_text()
        self._update_controls()

    def _refresh_case_text(self):
        step = self._step()
        case = self._case()
        self.lbl_mode.text = (tr('demo.complete_mode', order=self.mode)
                              if isinstance(self.mode, int) and 'initial' in case
                              else _mode_title(self.mode))
        self.lbl_title.text = tr("demo.title_step", cn=g(self._si),
                                 n=self._si + 1,
                                 title=tr(localized(step['title'])),
                                 i=self._si + 1, total=len(self._steps))
        self.lbl_desc.text = localized(step["desc"])
        self.lbl_case.text = tr("demo.case", name=tr(localized(case['name'])))
        self.lbl_text.text = localized(case["text"])
        self.lbl_tip.text = localized(case["tip"])

    # ---- 播放动画 ----
    def to_start(self):
        """回到该案例的初始状态（停止播放并复位魔方），便于反复播放。"""
        self._show_case()

    def play(self):
        if self._playing:
            self._stop()
            return
        if self._busy or not self._moves:
            return
        if self._move_index >= len(self._moves):
            self._show_case()
        self._playing = True
        self._advance()

    def prev_move(self):
        if self._busy or self._move_index <= 0:
            return
        self._playing = False
        move = _inverse_demo_move(self._moves[self._move_index - 1], self._work)
        self._start_move(move, self._move_index - 1)

    def next_move(self):
        if self._busy or self._move_index >= len(self._moves):
            return
        self._playing = False
        self._advance()

    def _advance(self):
        if self._busy:
            return
        if self._move_index >= len(self._moves):
            self._playing = False
            self._update_controls()
            return
        self._start_move(self._moves[self._move_index], self._move_index + 1)

    def _start_move(self, move, target_index):
        if isinstance(move, str) and getattr(self._work, 'standard_notation', False):
            from demo.formula_notation import animation_steps
            self._queue = list(animation_steps(move, self._work))
        else:
            self._queue = list(decompose_move(move, self._work.n)) if isinstance(move, str) else []
        self._busy = True
        self._pending_index = target_index
        self._pending_move = move
        self._update_controls()
        if isinstance(move, str):
            self._step_queue()
        else:
            target=square1_target(move) if getattr(self._work,'puzzle_kind',None)=='square1' else polyhedral_target(self._work,move)
            def begin():
                if self._pending_move is not move:
                    return
                if self.view.animate_move(move,on_done=self._step_queue,duration=.5) is False:
                    self._stop()
            follow_turn(self.view,target,begin)

    def _step_queue(self):
        if self._queue:
            step = self._queue.pop(0)
            self._animate_step(step)
        else:
            if self._pending_index is not None:
                self._move_index = self._pending_index
            self._pending_index = None
            self._pending_move = None
            self._busy = False
            if self._move_index >= len(self._moves):
                self._playing = False
            self._update_controls()
            if self._playing:
                self._advance()

    def _animate_step(self, step):
        dur = 0.5 * abs(step.angle) / 90.0
        def begin():
            if not self._busy:
                return
            self.view.start_turn(step.axis,step.layers[0],step.angle,dur,
                                 on_done=lambda:self._after_turn(step),layer_positions=step.layers,
                                 include_fixed_centers=getattr(self._work, 'standard_notation', False) or step.move_str[:1] in ('x','y','z'))
        follow_turn(self.view,layer_target(step.axis,step.layers),begin)

    def _after_turn(self, step):
        if not self._busy or self._pending_index is None:
            return
        self._work.apply_move(step.move_str)
        _set_demo_cube(self.view, self._work, getattr(self, "_highlight", None))
        self._step_queue()

    def _stop(self):
        interrupted = self._busy
        self._playing = False
        self._busy = False
        self._queue = []
        self._pending_index = None
        self._pending_move = None
        cancel_follow(self.view)
        if hasattr(self.view, "_cancel_animation"):
            self.view._cancel_animation()
        elif hasattr(self.view, 'cancel_animation'):
            self.view.cancel_animation()
        if interrupted and self._initial is not None:
            # Keep the state at the last fully completed formula action.
            self._work = self._initial.clone()
            for move in self._moves[:self._move_index]:
                self._work.apply_move(move)
            _set_demo_cube(self.view, self._work, self._highlight)
        self._update_controls()

    def _update_controls(self):
        self.btn_prev.disabled = self._busy or self._move_index <= 0
        self.btn_next.disabled = self._busy or self._move_index >= len(self._moves)
        self.btn_start.disabled = self._move_index == 0 and not self._busy
        self.btn_play.disabled = not self._moves or (self._busy and not self._playing)
        self.btn_play.icon_name = "stop" if self._playing else "solve"
        move = self._pending_move or (
            self._moves[self._move_index - 1] if self._move_index else tr("playback.ready")
        )
        spec=getattr(getattr(self._work,'geometry',None),'spec',None)
        move_text=token(move,spec)
        if getattr(self._work,'puzzle_kind',None)=='blossom' and not isinstance(move,str):
            from cube.polyhedral import dot
            spec=self._work.geometry.spec
            axis=spec.axes[move.axis]
            nearest=max(dot(normal,axis) for normal in spec.normals)
            faces='/'.join(str(i+1) for i,normal in enumerate(spec.normals)
                           if abs(dot(normal,axis)-nearest)<1e-7)
            move_text=tr('poly.blossom_turn',faces=faces)
        self.lbl_progress.text = tr(
            "demo.progress", i=self._move_index, total=len(self._moves), move=move_text,
        )

    def on_pre_leave(self, *args):
        self._stop()

    def go_menu(self):
        self._stop()
        if getattr(self, '_return_screen', None):
            self.manager.current = self._return_screen
            return
        self.manager.get_screen("DemoMenuScreen").set_mode(self.mode)
        self.manager.current = "DemoMenuScreen"

    def go_home(self):
        self._stop()
        self.manager.current = "HomeScreen"


def g(n):
    """把 0/1/2.. 转成中文序号。"""
    return ["一", "二", "三", "四", "五", "六", "七", "八", "九"][n]


def _changed_homes(cube):
    """返回"状态已改变"的块的 home 身份集合。

    判据：位置 != home，或任一贴纸颜色与该位置该面标准色不符（覆盖原地扭转/翻转）。
    中心块不纳入（渲染时始终保留颜色作参照）。
    """
    from cube.coordinates import FACE_NORMALS, FACE_AXIS_SIGN

    def _axis(nv):
        for i, v in enumerate(nv):
            if abs(v):
                return i
        return 0

    def _sign(nv):
        for v in nv:
            if abs(v):
                return 1 if v > 0 else -1
        return 1

    normal_color = {}
    for face, (ax, sn) in FACE_AXIS_SIGN.items():
        normal_color[tuple(FACE_NORMALS[face])] = TEACHING_COLORS[face]

    out = set()
    for pos, c in cube.cubies.items():
        if len(c.stickers) == 1:
            continue  # 中心块
        changed = c.pos != c.home
        if not changed:
            for normal, col in c.stickers.items():
                expected = normal_color[tuple(normal)]
                if col != expected:
                    changed = True
                    break
        if changed:
            out.add(c.home)
    return out


def _app():
    from kivy.app import App
    return App.get_running_app()
