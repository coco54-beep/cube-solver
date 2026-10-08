"""演示页：用 3D 动画展示 2 阶分层法 / 3 阶七步法 / 4 阶与 5 阶降阶法的标准案例。

每个案例先摆出「初始状态」（= 还原魔方施加公式的逆），再逐式播放公式，
动画结束后回到还原态；同时显示步骤、案例名、公式与记忆口诀。
5 阶只收录与四阶不同的部分（中心 3×3 / 三块棱配对）。
"""

from kivy.uix.boxlayout import BoxLayout
from ui.widgets.buttons import UIButton, PrimaryButton, ArrowButton
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from cube.cube2 import Cube2
from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.cube5 import Cube5
from cube.mastermorphix import MastermorphixCube
from demo.cases import (
    CASE_2X2, CASE_3X3, CASE_4X4, CASE_5X5,
    build_before, inverse_move_str, localized,
)
from demo.mastermorphix_cases import CASE_MASTERMORPHIX
from app.i18n import tr
from app.mastermorphix_palette import load_palette
from renderer.cube_view import CubeView
from renderer.mastermorphix_view import MastermorphixView, cube_view_for
from renderer.turn import decompose_move
from ui.widgets import metrics as m
from ui.widgets.layouts import ResponsiveBoxLayout, AdaptiveSceneLayout


def _theme():
    from kivy.app import App
    return App.get_running_app().theme


def _mode_title(n):
    return tr(f"demo.mode.title.{n}")


DEMO_MODES = (2, 3, 4, 5, "mastermorphix")


def _steps_for(n):
    return {2: CASE_2X2, 3: CASE_3X3, 4: CASE_4X4, 5: CASE_5X5,
            "mastermorphix": CASE_MASTERMORPHIX}[n]


def _cls_for(n):
    return {2: Cube2, 3: Cube3, 4: Cube4, 5: Cube5}[n]


def _build_case_cube(mode, case):
    if mode == "mastermorphix":
        palette = load_palette()
        factory = lambda: MastermorphixCube.solved(palette)
    else:
        factory = _cls_for(mode).solved
    return build_before(factory, case["moves"])


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
        self.btn_reset.bind(on_release=lambda *a: self.view.reset_camera())
        for b in (self.btn_start, self.btn_prev, self.btn_play,
                  self.btn_next, self.btn_reset):
            control.add_widget(b)
        panel.add_widget(control)
        root.set_content(self.view, panel, portrait_fraction=.5)

        self.add_widget(root)
        self._update_controls()

    def retranslate(self):
        if not hasattr(self, "lbl_mode"):
            return
        self.lbl_mode.text = _mode_title(self.mode)
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
    def enter_case(self, mode, si, ci):
        """从目录跳到指定案例。"""
        self.mode = mode
        self._steps = _steps_for(mode)
        self.lbl_mode.text = _mode_title(mode)
        self._si = si
        self._ci = ci
        self._show_case()
        if self.mode == "mastermorphix":
            self.view.reset_camera()

    def toggle_mode(self):
        self.mode = DEMO_MODES[(DEMO_MODES.index(self.mode) + 1) % len(DEMO_MODES)]
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
        expected_view = MastermorphixView if self.mode == "mastermorphix" else CubeView
        if type(self.view) is not expected_view:
            self.view = cube_view_for(cube, size_hint_y=0.5)
            self._root_layout.replace_scene(self.view)
        if self.mode == "mastermorphix":
            self.view.show_axes = True
        self._work = cube
        self._initial = cube.clone()
        self._moves = list(case["moves"])
        self._move_index = 0
        # 聚焦：只给被移动/参与公式的块上色，其余灰色
        self._highlight = None if self.mode == "mastermorphix" else _changed_homes(cube)
        self.view.set_cube(cube, highlight=self._highlight)
        self._refresh_case_text()
        self._update_controls()

    def _refresh_case_text(self):
        step = self._step()
        case = self._case()
        self.lbl_title.text = tr("demo.title_step", cn=g(self._si),
                                 n=self._si + 1,
                                 title=localized(step['title']),
                                 i=self._si + 1, total=len(self._steps))
        self.lbl_desc.text = localized(step["desc"])
        self.lbl_case.text = tr("demo.case", name=localized(case['name']))
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
        move = inverse_move_str(self._moves[self._move_index - 1])
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
        self._queue = list(decompose_move(move, self._work.n))
        self._busy = True
        self._pending_index = target_index
        self._pending_move = move
        self._update_controls()
        self._step_queue()

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
        self.view.start_turn(
            step.axis,
            step.layers[0],
            step.angle,
            dur,
            on_done=lambda: self._after_turn(step),
            layer_positions=step.layers,
        )

    def _after_turn(self, step):
        if not self._busy or self._pending_index is None:
            return
        self._work.apply_move(step.move_str)
        self.view.set_cube(self._work, highlight=getattr(self, "_highlight", None))
        self._step_queue()

    def _stop(self):
        interrupted = self._busy
        self._playing = False
        self._busy = False
        self._queue = []
        self._pending_index = None
        self._pending_move = None
        if hasattr(self.view, "_cancel_animation"):
            self.view._cancel_animation()
        if interrupted and self._initial is not None:
            # Keep the state at the last fully completed formula action.
            self._work = self._initial.clone()
            self._work.apply_moves(self._moves[:self._move_index])
            self.view.set_cube(self._work, highlight=self._highlight)
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
        self.lbl_progress.text = tr(
            "demo.progress", i=self._move_index, total=len(self._moves), move=move,
        )

    def on_pre_leave(self, *args):
        self._stop()

    def go_menu(self):
        self._stop()
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
    from cube.colors import DEFAULT_COLORS
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
        normal_color[tuple(FACE_NORMALS[face])] = DEFAULT_COLORS[face]

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
