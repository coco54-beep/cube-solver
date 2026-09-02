"""回放页：3D 演示还原步骤，支持上一步/下一步/自动播放/暂停/速度。"""

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.slider import Slider

from renderer.cube_view import CubeView
from renderer.turn import decompose_move


class PlaybackScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._work = None       # 当前已回放到的立方体副本
        self._moves = []        # 动作列表（含宽层记号）
        self._idx = -1          # 已执行的步数
        self._playing = False
        self._speed = 1.0
        self._busy = False
        self._queue = []        # 待播放的 MoveStep 队列

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=4, padding=6)
        self.view = CubeView(size_hint_y=0.55)
        root.add_widget(self.view)

        info = BoxLayout(size_hint_y=0.08, spacing=6)
        self.lbl_stage = Label(text="", font_size="15sp", size_hint_x=0.55)
        self.lbl_move = Label(text="", font_size="18sp", size_hint_x=0.45)
        info.add_widget(self.lbl_stage)
        info.add_widget(self.lbl_move)
        root.add_widget(info)

        # 播放控制（两行：播放步进 + 视角/返回）
        control = BoxLayout(orientation="vertical", size_hint_y=0.22, spacing=6)
        play_row = BoxLayout(spacing=6)
        self.btn_start = Button(text="回到初始", font_size="15sp")
        self.btn_start.bind(on_release=lambda *a: self.to_start())
        self.btn_prev = Button(text="上一步", font_size="15sp")
        self.btn_prev.bind(on_release=lambda *a: self.prev())
        self.btn_play = Button(text="播放", font_size="15sp")
        self.btn_play.bind(on_release=lambda *a: self.toggle_play())
        self.btn_next = Button(text="下一步", font_size="15sp")
        self.btn_next.bind(on_release=lambda *a: self.next())
        self.btn_end = Button(text="跳结尾", font_size="15sp")
        self.btn_end.bind(on_release=lambda *a: self.to_end())
        for b in (self.btn_start, self.btn_prev, self.btn_play, self.btn_next, self.btn_end):
            play_row.add_widget(b)
        control.add_widget(play_row)
        util_row = BoxLayout(spacing=6)
        self.btn_view = Button(text="还原视角", font_size="15sp")
        self.btn_view.bind(on_release=lambda *a: self.reset_view())
        self.btn_back = Button(text="返回录入", font_size="15sp")
        self.btn_back.bind(on_release=lambda *a: self.go_back())
        for b in (self.btn_view, self.btn_back):
            util_row.add_widget(b)
        control.add_widget(util_row)
        root.add_widget(control)

        speed_row = BoxLayout(size_hint_y=0.08, spacing=6)
        speed_row.add_widget(Label(text="速度", font_size="15sp", size_hint_x=0.2))
        self.slider = Slider(min=0.25, max=2.0, value=1.0, step=0.25, size_hint_x=0.8)
        self.slider.bind(value=self._on_speed)
        speed_row.add_widget(self.slider)
        root.add_widget(speed_row)

        self.add_widget(root)

    def on_enter(self):
        if not hasattr(self, "view"):
            self.build_ui()
        app = _app()
        result = app.solve_result
        self._stop_all()
        self._work = app.cube.clone()
        self.view.set_cube(self._work)
        self._moves = list(result.moves) if result else []
        self._idx = -1
        self._queue = []
        self._busy = False
        self.lbl_move.text = f"共 {len(self._moves)} 步"
        self.lbl_stage.text = ""
        self._update_buttons()

    def _stop_all(self):
        self._playing = False
        self._busy = False
        self._queue = []
        # 取消 CubeView 正在进行的动画（若在播放中点跳结尾/上一步）
        if hasattr(self.view, "_cancel_animation"):
            self.view._cancel_animation()
        self.view._anim = None
        self.view._draw_mesh()
        self._update_buttons()

    # ---- 播放 ----
    def toggle_play(self):
        if self._playing:
            self._playing = False
        else:
            self._playing = True
            self._advance()
        self._update_buttons()

    def _on_speed(self, instance, value):
        self._speed = value

    def next(self):
        self._playing = False
        self._update_buttons()
        self._advance()

    def prev(self):
        self._playing = False
        # 撤回到上一步前：重放 0..idx-1
        self._idx = max(-1, self._idx - 1)
        self._replay_to(self._idx)

    def to_end(self):
        self._playing = False
        self._replay_to(len(self._moves) - 1)

    def to_start(self):
        """回到初始状态（跳结尾的对称操作）。"""
        self._playing = False
        self._replay_to(-1)

    def _advance(self):
        if self._busy:
            return
        if self._idx + 1 >= len(self._moves):
            self._playing = False
            self._update_buttons()
            return
        self._idx += 1
        mv = self._moves[self._idx]
        self._play_move(mv)

    def _play_move(self, move_str):
        steps = decompose_move(move_str, _app().n)
        self._queue = steps
        self._busy = True
        self._step_queue()

    def _step_queue(self):
        if self._queue:
            step = self._queue.pop(0)
            self._animate_step(step)
        else:
            self._busy = False
            self._update_buttons()
            if self._playing:
                self._advance()

    def _animate_step(self, step):
        # 用 CubeView.start_turn 驱动动画（内部用 Clock.schedule_interval 逐帧推进）。
        # wide 层转动传 layer_positions=step.layers，让动画覆盖所有层。
        # duration 按角度成比例（90° 为基准），让 90/180/270 度转速恒定，
        # 避免大角度动作在固定时长内转得过快。
        dur = 0.35 * abs(step.angle) / 90.0 / self._speed
        self.view.start_turn(
            step.axis,
            step.layers[0],
            step.angle,
            dur,
            on_done=lambda: self._after_turn(step),
            layer_positions=step.layers,
        )

    def _after_turn(self, step):
        # 动画结束：应用 step 表示的一次转动（可能 90/180/270 度）到逻辑状态。
        mv = _single_turn_string(step)
        for _ in range(step.count):
            self._work.apply_move(mv)
        self.view.set_cube(self._work)
        self._step_queue()

    def _replay_to(self, idx):
        # 重建到第 idx 步
        self._stop_all()
        if not self._moves:
            self._work = _app().cube.clone()
            self.view.set_cube(self._work)
            self._idx = -1
            self._update_buttons()
            return
        self._work = _app().cube.clone()
        self.view.set_cube(self._work)
        self._idx = -1
        target = min(max(idx, -1), len(self._moves) - 1)
        while self._idx < target:
            self._idx += 1
            mv = self._moves[self._idx]
            self._work.apply_moves([mv])
        self.view.set_cube(self._work)
        self._update_buttons()

    def _update_buttons(self):
        self.lbl_move.text = f"第 {max(0,self._idx+1)}/{len(self._moves)} 步"
        self.btn_start.disabled = self._idx < 0
        self.btn_prev.disabled = self._idx < 0
        self.btn_next.disabled = self._idx + 1 >= len(self._moves)
        self.btn_play.text = "暂停" if self._playing else "播放"

    def reset_view(self):
        """把 3D 视角还原到默认。"""
        self.view.reset_camera()

    def go_home(self):
        self._stop_all()
        self.manager.current = "HomeScreen"

    def go_back(self):
        """返回录入页：自动恢复上次布局（如布局未变，开始求解时会复用上次方案）。"""
        self._stop_all()
        self.manager.current = "InputScreen"


def _app():
    from kivy.app import App
    return App.get_running_app()


def _single_turn_string(step):
    """返回表示 step 一次 90° 的动作字符串（base + 可选宽层小写）。"""
    base = step.base
    if step.wide:
        return base.lower()
    return base

