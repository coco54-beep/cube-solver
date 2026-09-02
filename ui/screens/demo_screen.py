"""演示页：用 3D 动画展示 3 阶七步法 / 4 阶降阶法的标准案例。

每个案例先摆出「初始状态」（= 还原魔方施加公式的逆），再逐式播放公式，
动画结束后回到还原态；同时显示步骤、案例名、公式与记忆口诀。
"""

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from cube.cube3 import Cube3
from cube.cube4 import Cube4
from demo.cases import CASE_3X3, CASE_4X4, build_before
from renderer.cube_view import CubeView
from renderer.turn import decompose_move


class DemoScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = 3
        self._steps = CASE_3X3
        self._si = 0
        self._ci = 0
        self._work = None
        self._queue = []
        self._busy = False
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=4, padding=[8, 6, 8, 8])

        # 顶栏：返回目录 + 标题 + 播放
        top = BoxLayout(size_hint_y=None, height=46, spacing=6)
        back = Button(text="←目录", size_hint_x=0.2)
        back.bind(on_release=lambda *a: self.go_menu())
        self.lbl_mode = Label(text="3阶 · 七步法", size_hint_x=0.45, halign="center",
                              bold=True, font_size="18sp")
        btn = Button(text="切换 3/4 阶", size_hint_x=0.35)
        btn.bind(on_release=lambda *a: self.toggle_mode())
        top.add_widget(back)
        top.add_widget(self.lbl_mode)
        top.add_widget(btn)
        root.add_widget(top)

        # 3D 视图
        self.view = CubeView(size_hint_y=0.52)
        root.add_widget(self.view)

        # 信息区
        info = BoxLayout(orientation="vertical", size_hint_y=None, height=196, spacing=2)
        self.lbl_title = Label(text="", font_size="17sp", bold=True, halign="left",
                               valign="middle", size_hint_y=None, height=30)
        self.lbl_desc = Label(text="", font_size="13sp", halign="left", valign="top",
                              color=(0.78, 0.82, 0.9, 1), size_hint_y=None, height=64)
        self.lbl_case = Label(text="", font_size="15sp", halign="left", valign="middle",
                              color=(0.9, 0.93, 0.98, 1), size_hint_y=None, height=24)
        self.lbl_text = Label(text="", font_size="18sp", halign="center", valign="middle",
                              bold=True, size_hint_y=None, height=40)
        self.lbl_tip = Label(text="", font_size="14sp", halign="center", valign="middle",
                             color=(0.8, 0.84, 0.9, 1), size_hint_y=None, height=28)
        # text_size 跟随 label 宽度，保证多行文本正常换行（避免竖排/裁剪）。
        for w in (self.lbl_desc, self.lbl_text, self.lbl_tip):
            w.bind(size=lambda ins, s: setattr(ins, "text_size", (s[0], None)))
        for w in (self.lbl_title, self.lbl_desc, self.lbl_case, self.lbl_text, self.lbl_tip):
            info.add_widget(w)
        root.add_widget(info)

        # 控制区
        ctl = BoxLayout(size_hint_y=None, height=52, spacing=6)
        prev = Button(text="上一步", size_hint_x=0.3)
        prev.bind(on_release=lambda *a: self.prev_case())
        self.btn_play = Button(text="播放", size_hint_x=0.2)
        self.btn_play.bind(on_release=lambda *a: self.play())
        nxt = Button(text="下一步", size_hint_x=0.3)
        nxt.bind(on_release=lambda *a: self.next_case())
        reset = Button(text="还原视角", size_hint_x=0.2)
        reset.bind(on_release=lambda *a: self.view.reset_camera())
        ctl.add_widget(prev)
        ctl.add_widget(self.btn_play)
        ctl.add_widget(nxt)
        ctl.add_widget(reset)
        root.add_widget(ctl)

        self.add_widget(root)

    # ---- 模式 / 导航 ----
    def enter_case(self, mode, si, ci):
        """从目录跳到指定案例。"""
        self.mode = mode
        self._steps = CASE_3X3 if mode == 3 else CASE_4X4
        self.lbl_mode.text = "3阶 · 七步法" if mode == 3 else "4阶 · 降阶法"
        self._si = si
        self._ci = ci
        self._show_case()

    def toggle_mode(self):
        self.mode = 3 if self.mode == 4 else 4
        self._steps = CASE_3X3 if self.mode == 3 else CASE_4X4
        self.lbl_mode.text = "3阶 · 七步法" if self.mode == 3 else "4阶 · 降阶法"
        self._si = 0
        self._ci = 0
        self._show_case()

    def prev_case(self):
        if self._ci > 0:
            self._ci -= 1
        elif self._si > 0:
            self._si -= 1
            self._ci = len(self._steps[self._si]["cases"]) - 1
        else:
            return
        self._show_case()

    def next_case(self):
        if self._ci < len(self._steps[self._si]["cases"]) - 1:
            self._ci += 1
        elif self._si < len(self._steps) - 1:
            self._si += 1
            self._ci = 0
        else:
            return
        self._show_case()

    def _step(self):
        return self._steps[self._si]

    def _case(self):
        return self._step()["cases"][self._ci]

    def _show_case(self):
        self._stop()
        step = self._step()
        case = self._case()
        cls = Cube3 if self.mode == 3 else Cube4
        cube = build_before(cls.solved, case["moves"])
        self._work = cube
        # 聚焦：只给被移动/参与公式的块上色，其余灰色
        self._highlight = _changed_homes(cube)
        self.view.set_cube(cube, highlight=self._highlight)
        self.lbl_title.text = f"第{g(self._si + 1)}步 · {step['title']}（{self._si + 1}/{len(self._steps)}）"
        self.lbl_desc.text = step["desc"]
        self.lbl_case.text = f"案例：{case['name']}"
        self.lbl_text.text = case["text"]
        self.lbl_tip.text = case["tip"]

    # ---- 播放动画 ----
    def play(self):
        if self._busy:
            return
        case = self._case()
        # 先还原到该案例的初始场景，再开始播放公式。
        cls = Cube3 if self.mode == 3 else Cube4
        cube = build_before(cls.solved, case["moves"])
        self._work = cube
        self._highlight = _changed_homes(cube)
        self.view.set_cube(cube, highlight=self._highlight)
        self._queue = []
        for m in case["moves"]:
            self._queue.extend(decompose_move(m, self.mode))
        self._busy = True
        self.btn_play.text = "播放中…"
        self._step_queue()

    def _step_queue(self):
        if self._queue:
            step = self._queue.pop(0)
            self._animate_step(step)
        else:
            self._busy = False
            self.btn_play.text = "播放"

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
        mv = _single_turn_string(step)
        for _ in range(step.count):
            self._work.apply_move(mv)
        self.view.set_cube(self._work, highlight=getattr(self, "_highlight", None))
        self._step_queue()

    def _stop(self):
        self._busy = False
        self._queue = []
        if hasattr(self.view, "_cancel_animation"):
            self.view._cancel_animation()
        self.btn_play.text = "播放"

    def go_menu(self):
        self._stop()
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


def _single_turn_string(step):
    base = step.base
    return base.lower() if step.wide else base


def _app():
    from kivy.app import App
    return App.get_running_app()
