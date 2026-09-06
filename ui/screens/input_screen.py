"""录入页：3D 单面填色输入 + 颜色选择 + 校验 + 求解。

与旧版展开图不同，此处用 CubeView 呈现一个完整的 3D 魔方，每次只有
一个面正对相机（展示面很大），使用户直接在该面上点击格子填色。
通过 "下一步/上一步" 按钮整体旋转魔方，切换当前填色面。
"""

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.screenmanager import Screen

from renderer.cube_view import CubeView
from renderer.cube_orientation import CubeOrientation

# 屏幕方位 -> 箭头字符（指示该侧的面将转到正面）
_DIR_ARROW = {
    "right": "→",
    "left": "←",
    "up": "↑",
    "down": "↓",
}


class PrimaryButton(Button):
    """主操作按钮（绿色主题，见 app.kv 的 <PrimaryButton> 规则）。"""
    pass


class DangerButton(Button):
    """危险操作按钮（红色主题，见 app.kv 的 <DangerButton> 规则）。"""
    pass


from app.constants import FACE_LABEL, FACES
from cube.conversion import facelets_to_cubies
from cube.cubie_model import Cubie
from cube.coordinates import FACE_NORMALS, pos_from_rc, get_d_maxc, rc_from_pos, coord_values
from cube.validation import validate_2x2, validate_3x3, validate_4x4, validate_5x5
from cube.cube2 import Cube2
from cube.cube4 import Cube4
from cube.cube3 import Cube3
from cube.cube5 import Cube5
from ui.widgets.color_picker import ColorSelector
from solver.solver4 import _rebuild_center_homes


def _axis_of(normal):
    """法线向量的主轴 (0/1/2)。"""
    for i, v in enumerate(normal):
        if abs(v) == 1:
            return i
    return 0


def _sign(normal):
    """法线向量的符号。"""
    for v in normal:
        if abs(v) == 1:
            return 1 if v > 0 else -1
    return 1


def _build_partial_cube(facelets, n):
    """从 facelets 构建 Cube，空格格子为深色、已填的按颜色显示。

    所有外表面位置都建 cubie；未填的 sticker 用空串占位（渲染时 scene
    会将其视为深色），让魔方保持完整轮廓，同时突出已填颜色。
    """
    from cube.cubie_model import Cubie

    cubies = {}
    d, maxc = get_d_maxc(n)
    vals = coord_values(n)
    for x in vals:
        for y in vals:
            for z in vals:
                pos = (x, y, z)
                stickers = {}
                for face in FACES:
                    normal = FACE_NORMALS[face]
                    if pos[_axis_of(normal)] != _sign(normal) * maxc:
                        continue
                    r, c = rc_from_pos(n, face, pos)
                    grid = facelets.get(face, [])
                    col = ""
                    if len(grid) > r and len(grid[r]) > c:
                        col = grid[r][c]
                    stickers[normal] = col
                if stickers:
                    cubies[pos] = Cubie(home=pos, pos=pos, stickers=stickers)
    if not cubies:
        return None
    if n == 2:
        return Cube2(cubies)
    if n == 4:
        return Cube4(cubies)
    if n == 5:
        return Cube5(cubies)
    return Cube3(cubies)


class _InputCubeView(CubeView):
    """3D 输入视图：允许缩放，但禁用拖拽旋转；单击回调 on_pick(x, y)，拖动回调 on_drag(x, y)。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on_pick = None
        self.on_drag = None
        self.on_drag_end = None
        self._press = None
        self._moved = False

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if getattr(touch, "is_mouse_scrolling", False):
            return super().on_touch_down(touch)
        self._press = touch.pos
        self._moved = False
        try:
            touch.grab(self)
        except Exception:
            pass
        return True

    def on_touch_move(self, touch):
        if self._press is not None:
            dx = touch.x - self._press[0]
            dy = touch.y - self._press[1]
            if dx * dx + dy * dy > 16 * 16:
                self._moved = True
        # 输入模式禁用拖拽旋转；仅上报拖动位置给连续填色回调。
        if self._moved and self.on_drag is not None:
            self.on_drag(touch.x, touch.y)
            return True
        return self._pass_rotate(touch)

    def _pass_rotate(self, touch):
        return CubeView.on_touch_move(self, touch)

    def on_touch_up(self, touch):
        if self._press is not None:
            was_drag = self._moved
            try:
                touch.ungrab(self)
            except Exception:
                pass
            self._press = None
            if was_drag:
                if self.on_drag_end is not None:
                    self.on_drag_end()
            elif self.on_pick is not None:
                self.on_pick(touch.x, touch.y)
            return True
        return CubeView.on_touch_up(self, touch)


class InputScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._data = {}          # {face: n x n matrix}
        self._ori = None         # CubeOrientation
        self._busy_turn = False
        self._pending_dir = None
        self._initialized = False
        self._pick_mode = False   # 吸色模式
        self._history = []        # 撤销栈：每个动作为 [(face, r, c, old, new), ...]
        self._redo = []           # 重做栈
        self._drag_edits = {}     # 当前拖动手法累积的编辑 {(r,c): old}
        self.build_ui()
        self._init_for_n()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=8, padding=[8, 6, 8, 8])

        # ---- 顶栏 ----
        top = BoxLayout(size_hint_y=None, height=46, spacing=8)
        back = Button(text="←返回", size_hint_x=0.22)
        back.bind(on_release=lambda *a: self.go_home())
        self.title = Label(text="录入 4x4", size_hint_x=0.56, halign="center",
                           font_size="20sp", bold=True)
        demo = Button(text="演示", size_hint_x=0.22)
        demo.bind(on_release=lambda *a: self.open_demo())
        top.add_widget(back)
        top.add_widget(self.title)
        top.add_widget(demo)
        root.add_widget(top)

        # ---- 3D 视图占满主区 ----
        self.view = _InputCubeView(size_hint=(1.0, 1.0))
        self.view.on_pick = self._handle_pick
        self.view.on_drag = self._handle_drag
        self.view.on_drag_end = self._handle_drag_end
        root.add_widget(self.view)

        # ---- 当前面 + 缩放 ----
        nav = BoxLayout(size_hint_y=None, height=44, spacing=8)
        zoom_in = Button(text="＋", size_hint_x=0.12, font_size="20sp")
        zoom_in.bind(on_release=lambda *a: self._zoom(1.15))
        zoom_out = Button(text="－", size_hint_x=0.12, font_size="20sp")
        zoom_out.bind(on_release=lambda *a: self._zoom(1 / 1.15))
        self.face_label = Label(text="当前面：前", size_hint_x=0.5,
                                halign="center", font_size="17sp", bold=True)
        for w in (zoom_out, self.face_label, zoom_in):
            nav.add_widget(w)
        root.add_widget(nav)

        # ---- 颜色选择器 ----
        self.picker = ColorSelector(size_hint_y=None, height=52)
        root.add_widget(self.picker)

        # ---- 录入辅助工具 ----
        edit_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        self.btn_pick = Button(text="吸色", font_size="15sp")
        self.btn_pick.bind(on_release=lambda *a: self.toggle_pick())
        self.btn_fill = Button(text="整面填充", font_size="15sp")
        self.btn_fill.bind(on_release=lambda *a: self.fill_face())
        self.btn_undo = Button(text="撤销", font_size="15sp")
        self.btn_undo.bind(on_release=lambda *a: self.undo())
        self.btn_redo = Button(text="重做", font_size="15sp")
        self.btn_redo.bind(on_release=lambda *a: self.redo())
        for b in (self.btn_pick, self.btn_fill, self.btn_undo, self.btn_redo):
            edit_row.add_widget(b)
        root.add_widget(edit_row)

        # ---- 翻转导航 ----
        turn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        self.btn_prev = Button(text="上一步", font_size="16sp")
        self.btn_prev.bind(on_release=lambda *a: self.prev_face())
        self.btn_next = Button(text="下一步", font_size="16sp")
        self.btn_next.bind(on_release=lambda *a: self.next_face())
        for b in (self.btn_prev, self.btn_next):
            turn_row.add_widget(b)
        root.add_widget(turn_row)

        # ---- 操作按钮行 ----
        action_row = BoxLayout(size_hint_y=None, height=52, spacing=8)
        rnd = Button(text="随机")
        rnd.bind(on_release=lambda *a: self.random_load())
        clear = DangerButton(text="清空")
        clear.bind(on_release=lambda *a: self.confirm_clear())
        check = Button(text="校验")
        check.bind(on_release=lambda *a: self.check())
        solve = PrimaryButton(text="开始求解")
        solve.bind(on_release=lambda *a: self.start_solve())
        for b in (rnd, clear, check, solve):
            action_row.add_widget(b)
        root.add_widget(action_row)

        # ---- 状态提示 ----
        self.msg = Label(text="", size_hint_y=None, height=34,
                         color=(1, 0.55, 0.55, 1), halign="center")
        root.add_widget(self.msg)
        self.add_widget(root)

        self.bind(size=self._on_resize)

    def _on_resize(self, *args):
        # 尺寸变化时重新取景（整体旋转与颜色数据保留）。
        Clock.schedule_once(lambda *a: self._refresh_view(keep_anim=False), 0)

    def _init_for_n(self):
        n = self._n()
        self._data = {f: [[""] * n for _ in range(n)] for f in FACES}
        self._ori = CubeOrientation(n)
        self.title.text = f"录入 {n}x{n}"
        # 录入页相机正对当前面（+Z），不使用演示页的斜视角度。
        self.view.camera.elevation = 0.0
        self.view.camera.azimuth = 0.0
        self.view._display_zoom = 1.0
        self._reset_edits()
        self._refresh_view()
        self._update_turn_hints()

    def _reset_edits(self):
        self._history = []
        self._redo = []
        self._drag_edits = {}
        self._pick_mode = False
        self.btn_pick.background_color = [0.5, 0.5, 0.5, 1]
        self._update_edit_buttons()

    def _n(self):
        return _app().n

    # ---- 3D 视图 ----
    def _refresh_view(self, keep_anim=True):
        if not hasattr(self, "view"):
            return
        facelets = self.collect_facelets()
        cube = _build_partial_cube(facelets, self._n())
        if cube is None:
            self.view.cube = None
            self.view._redraw()
            return
        if not keep_anim:
            self.view._cancel_whole_anim()
        self.view.set_cube(cube)
        self.view.set_whole_world(self._ori.world)
        self._update_face_label()

    def _update_face_label(self):
        face = self._ori.current_face()
        self.face_label.text = f"当前面：{FACE_LABEL.get(face, face)} ({face})"

    def _update_turn_hints(self):
        """在"上一步/下一步"按钮上显示本次转向的方位箭头。"""
        left = _DIR_ARROW.get(self._ori.prev_dir(), "◀")
        right = _DIR_ARROW.get(self._ori.next_dir(), "▶")
        self.btn_prev.text = f"{left}上一步"
        self.btn_next.text = f"{right}下一步"

    def _zoom(self, factor):
        self.view._display_zoom *= factor
        self.view._display_zoom = max(0.25, min(4.0, self.view._display_zoom))
        self.view._draw_mesh()

    def _handle_pick(self, x, y):
        if self._busy_turn:
            return
        face = self._ori.current_face()
        hit = self.view.pick_cell(face, self._n(), x, y)
        if hit is None:
            return
        r, c = hit
        if self._pick_mode:
            col = self._data[face][r][c]
            if col:
                self.picker.select(col)
                self.toggle_pick()
                self.msg.text = f"已吸色 {col}，可继续填色"
            return
        self.on_cell(r, c, face)

    def _handle_drag(self, x, y):
        if self._busy_turn or self._pick_mode:
            return
        face = self._ori.current_face()
        hit = self.view.pick_cell(face, self._n(), x, y)
        if hit is None:
            return
        r, c = hit
        self._fill_cell(face, r, c, self.picker.current_color,
                        action=self._drag_edits)

    def _handle_drag_end(self):
        if self._drag_edits:
            self._commit_action(self._drag_edits)
            self._drag_edits = {}
            self._refresh_view()

    # ---- 颜色填充 ----
    def _fill_cell(self, face, r, c, col, action=None):
        """填一个格子；若给定 action 字典则记录旧值（供连续拖动合并一次撤销）。"""
        old = self._data[face][r][c]
        if old == col:
            return
        if action is not None:
            if (r, c) not in action:
                action[(r, c)] = old
        self._data[face][r][c] = col
        self.msg.text = ""
        if action is None:
            self._commit_action({(r, c): old})
        self._refresh_view()

    def _commit_action(self, edits):
        """把一次编辑（多为 dict {(r,c): old}）压入撤销栈，并清空重做栈。"""
        face = self._ori.current_face()
        action = [(face, r, c, old, self._data[face][r][c])
                  for (r, c), old in edits.items()]
        if action:
            self._history.append(action)
            self._redo = []
        self._update_edit_buttons()

    def fill_face(self):
        """把当前面所有格子填成当前色（作为一次可撤销操作）。"""
        if self._busy_turn:
            return
        face = self._ori.current_face()
        col = self.picker.current_color
        n = self._n()
        edits = {}
        for r in range(n):
            for c in range(n):
                if self._data[face][r][c] != col:
                    edits[(r, c)] = self._data[face][r][c]
                    self._data[face][r][c] = col
        if edits:
            self._commit_action(edits)
            self.msg.text = f"已将 {face} 面填充为 {col}"
        else:
            self.msg.text = f"{face} 面已是 {col}"
        self._refresh_view()

    def toggle_pick(self):
        self._pick_mode = not self._pick_mode
        self.btn_pick.background_color = (
            [0.25, 0.55, 0.95, 1] if self._pick_mode else [0.5, 0.5, 0.5, 1])

    # ---- 撤销 / 重做 ----
    def undo(self):
        if not self._history:
            return
        action = self._history.pop()
        for face, r, c, old, _new in reversed(action):
            self._data[face][r][c] = old
        self._redo.append(action)
        self.msg.text = "已撤销"
        self._refresh_view()
        self._update_edit_buttons()

    def redo(self):
        if not self._redo:
            return
        action = self._redo.pop()
        for face, r, c, _old, new in action:
            self._data[face][r][c] = new
        self._history.append(action)
        self.msg.text = "已重做"
        self._refresh_view()
        self._update_edit_buttons()

    def _update_edit_buttons(self):
        self.btn_undo.disabled = not self._history
        self.btn_redo.disabled = not self._redo

    def next_face(self):
        self._animate_turn("next")

    def prev_face(self):
        self._animate_turn("prev")

    def _animate_turn(self, direction):
        if self._busy_turn:
            return
        self._busy_turn = True
        self._pending_dir = direction
        if direction == "prev":
            angle, axis = self._ori.prev_axis_deg()
        else:
            angle, axis = self._ori.next_axis_deg()
        self.view.animate_whole_turn(
            axis, angle, 0.55, on_done=lambda: self._after_turn()
        )

    def _after_turn(self):
        if getattr(self, "_pending_dir", None) == "prev":
            self._ori.turn_prev()
        else:
            self._ori.turn_next()
        self._pending_dir = None
        self._busy_turn = False
        self._update_face_label()
        self._update_turn_hints()

    # ---- 数据存取 ----
    def collect_facelets(self):
        return {f: [row[:] for row in self._data.get(f, [])] for f in FACES}

    def set_facelets(self, facelets):
        n = self._n()
        for f in FACES:
            if f in facelets:
                grid = facelets[f]
                self._data[f] = [[grid[r][c] for c in range(n)]
                                 for r in range(n)]
        self._reset_edits()
        self._refresh_view()

    def on_cell(self, r, c, face):
        col = self.picker.current_color
        self._fill_cell(face, r, c, col)

    def random_load(self):
        import random
        from cube.cube2 import Cube2
        from cube.cube4 import Cube4
        from cube.cube3 import Cube3
        from cube.cube5 import Cube5
        from cube.conversion import cubies_to_facelets
        n = self._n()
        if n == 2:
            cube = Cube2.solved()
        elif n == 4:
            cube = Cube4.solved()
        elif n == 5:
            cube = Cube5.solved()
        else:
            cube = Cube3.solved()
        if n == 4:
            faces = ["U", "D", "F", "B", "R", "L", "u", "d", "f", "b", "r", "l"]
        elif n == 5:
            faces = ["U", "D", "F", "B", "R", "L", "u", "d", "f", "b", "r", "l",
                     "2U", "2D", "2F", "2B", "2R", "2L"]
        else:
            faces = ["U", "D", "F", "B", "R", "L"]
        suff = ["", "'", "2"]
        moves = [random.choice(faces) + random.choice(suff)
                 for _ in range(random.randint(12, 25))]
        cube.apply_moves(moves)
        facelets = cubies_to_facelets(cube.cubies, n)
        self.set_facelets(facelets)
        self.msg.text = f"已加载随机布局（{len(moves)} 步打乱）"

    def confirm_clear(self):
        from kivy.uix.popup import Popup
        content = BoxLayout(orientation="vertical", spacing=12, padding=16)
        label = Label(text="确定要清空全部已录入的颜色吗？", halign="center",
                      font_size="18sp", size_hint_y=1)
        btns = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=52)
        cancel = Button(text="取消")
        cancel.bind(on_release=lambda *a: popup.dismiss())
        ok = DangerButton(text="确定清空")
        ok.bind(on_release=lambda *a: (self.clear_all(), popup.dismiss()))
        btns.add_widget(cancel)
        btns.add_widget(ok)
        content.add_widget(label)
        content.add_widget(btns)
        popup = Popup(title="确认清空", content=content, size_hint=(0.86, 0.34))
        popup.bind(on_dismiss=lambda *a: None)
        popup.open()

    def clear_all(self):
        n = self._n()
        for face in FACES:
            self._data[face] = [[""] * n for _ in range(n)]
        self._ori = CubeOrientation(n)
        self._busy_turn = False
        self._pending_dir = None
        self._reset_edits()
        self._refresh_view()
        self.msg.text = "已清空"

    def reset_all(self):
        self._init_for_n()

    def on_enter(self):
        n = self._n()
        self.title.text = f"录入 {n}x{n}"
        if not self._initialized or getattr(self, "_n_for_screen", None) != n:
            self._init_for_n()
            self._n_for_screen = n
            self._initialized = True
        app = _app()
        if app.facelets_input is not None:
            self.set_facelets(app.facelets_input)
            self.msg.text = "已加载上次布局，直接点「开始求解」可沿用上次方案"

    # ---- 校验 ----
    def check(self):
        facelets = self.collect_facelets()
        n = self._n()
        empty = []
        for face in FACES:
            for r in range(n):
                for c in range(n):
                    if not facelets[face][r][c]:
                        empty.append(f"{FACE_LABEL[face]}{r+1}{c+1}")
        if empty:
            self.msg.text = f"未填写: {','.join(empty[:8])}"
            return
        if n == 2:
            errs = validate_2x2(facelets)
        elif n == 3:
            errs = validate_3x3(facelets)
        elif n == 5:
            errs = validate_5x5(facelets)
        else:
            errs = validate_4x4(facelets)
        if errs:
            self.msg.text = errs[0]
        else:
            self.msg.text = "状态合法 ✓"

    # ---- 求解 ----
    def start_solve(self):
        self.check()
        if self.msg.text != "状态合法 ✓":
            return
        app = _app()
        facelets = self.collect_facelets()
        prev_result = app.solve_result
        prev_layout = app.facelets_input
        reuse = prev_result is not None and prev_layout == facelets
        self._commit_cube(facelets)
        if reuse:
            app.solve_result = prev_result
            self.manager.current = "PlaybackScreen"
        else:
            self.manager.current = "SolvingScreen"

    def _commit_cube(self, facelets):
        app = _app()
        cubies = facelets_to_cubies(facelets, self._n())
        if self._n() == 4:
            _rebuild_center_homes(cubies)
        app.set_cube(cubies, self._n())
        app.facelets_input = facelets

    def go_home(self):
        self.manager.current = "HomeScreen"

    def open_demo(self):
        app = _app()
        app.facelets_input = self.collect_facelets()
        menu = self.manager.get_screen("DemoMenuScreen")
        menu.set_mode(self._n())
        self.manager.current = "DemoMenuScreen"


def _app():
    from kivy.app import App
    return App.get_running_app()
