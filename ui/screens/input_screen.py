"""录入页：3D 单面填色输入 + 颜色选择 + 校验 + 求解。

与旧版展开图不同，此处用 CubeView 呈现一个完整的 3D 魔方，每次只有
一个面正对相机（展示面很大），使用户直接在该面上点击格子填色。
通过 "下一步/上一步" 按钮整体旋转魔方，切换当前填色面。
"""

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.screenmanager import Screen

from ui.widgets.buttons import UIButton, PrimaryButton, DangerButton, ArrowButton

from renderer.cube_view import CubeView
from renderer.cube_orientation import CubeOrientation


from app.constants import FACES
from app.i18n import tr, current_language
from cube.conversion import facelets_to_cubies
from cube.cubie_model import Cubie
from cube.coordinates import FACE_NORMALS, pos_from_rc, get_d_maxc, rc_from_pos, coord_values
from cube.validation import validate_2x2, validate_3x3, validate_4x4, validate_5x5
from cube.cube2 import Cube2
from cube.cube4 import Cube4
from cube.cube3 import Cube3
from cube.cube5 import Cube5
from cube.cube_n import CubeN
from cube.colors import DEFAULT_COLORS
from ui.widgets.color_picker import ColorSelector
from ui.widgets import metrics as m
from ui.widgets.layouts import AdaptiveSceneLayout, ResponsiveBoxLayout


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
    if n >= 6:
        return CubeN(cubies, n)
    return Cube3(cubies)


def _new_solved_cube(n):
    """按阶数创建已还原魔方（用于随机/公式打乱）。"""
    if n == 2:
        return Cube2.solved()
    if n == 4:
        return Cube4.solved()
    if n == 5:
        return Cube5.solved()
    if n >= 6:
        return CubeN.solved(n)
    return Cube3.solved()


class _InputCubeView(CubeView):
    """3D 输入视图：允许缩放，但禁用拖拽旋转；单击回调 on_pick(x, y)，拖动回调 on_drag(x, y)。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on_pick = None
        self.on_drag = None
        self.on_drag_end = None
        self._press = None
        self._moved = False
        # 只处理「本视图按下」的那一个触点；否则从颜色选择器等其它控件冒泡上来的
        # touch_up 会带着它们的坐标触发 on_pick，误填到当前面的角落。
        self._active_touch = None

    def cancel_touch(self):
        """Release a gesture even if the OS never delivered its touch-up."""
        touch = self._active_touch
        self._active_touch = None
        self._press = None
        self._moved = False
        if touch is not None:
            try:
                touch.ungrab(self)
            except Exception:
                pass

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if getattr(touch, "is_mouse_scrolling", False):
            return super().on_touch_down(touch)
        if self._active_touch is not None:
            return False
        self._active_touch = touch
        self._press = touch.pos
        self._moved = False
        try:
            touch.grab(self)
        except Exception:
            pass
        return True

    def on_touch_move(self, touch):
        if touch is not self._active_touch:
            return False
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
        if touch is not self._active_touch:
            return False
        was_drag = self._moved
        self.cancel_touch()
        if was_drag:
            if self.on_drag_end is not None:
                self.on_drag_end()
        elif self.on_pick is not None:
            self.on_pick(touch.x, touch.y)
        return True


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
        self._error_cells = set()
        self.build_ui()
        self._init_for_n()

    def build_ui(self):
        simple = bool(getattr(_app(), "simple_input", False))
        self._simple = simple
        root = AdaptiveSceneLayout()
        panel = ResponsiveBoxLayout(orientation="vertical", gap_px=8, size_hint_y=None)

        # ---- 顶栏 ----
        top = BoxLayout(size_hint_y=None, height=m.h(48), spacing=8)
        self.btn_back = UIButton(text="", icon_name="back", size_hint_x=0.22)
        self.btn_back.bind(on_release=lambda *a: self.go_home())
        self.title = Label(text=tr("input.title", n=self._n()),
                           size_hint_x=(0.78 if simple else 0.56),
                           halign="center", font_size="20sp", bold=True)
        self.btn_demo = UIButton(text="", icon_name="demo", size_hint_x=0.22)
        self.btn_demo.bind(on_release=lambda *a: self.open_demo())
        top.add_widget(self.btn_back)
        top.add_widget(self.title)
        if not simple:
            top.add_widget(self.btn_demo)
        root.add_widget(top)

        # ---- 3D 视图占满主区 ----
        self.view = _InputCubeView(size_hint=(1.0, 1.0))
        self.view.on_pick = self._handle_pick
        self.view.on_drag = self._handle_drag
        self.view.on_drag_end = self._handle_drag_end

        # ---- 当前面 + 缩放（简洁模式只留当前面）----
        nav = BoxLayout(size_hint_y=None, height=m.h(48), spacing=8)
        self.btn_zoom_in = UIButton(text="", icon_name="zoom_in", size_hint_x=0.12)
        self.btn_zoom_in.bind(on_release=lambda *a: self._zoom(1.15))
        self.btn_zoom_out = UIButton(text="", icon_name="zoom_out", size_hint_x=0.12)
        self.btn_zoom_out.bind(on_release=lambda *a: self._zoom(1 / 1.15))
        self.face_label = Label(text=tr("input.face", face=tr("face.F"), code="F"),
                                size_hint_x=(1.0 if simple else 0.5), halign="center",
                                font_size=("14sp" if simple else "17sp"), bold=True)
        if simple:
            nav.add_widget(self.face_label)
        else:
            for w in (self.btn_zoom_out, self.face_label, self.btn_zoom_in):
                nav.add_widget(w)
        panel.add_widget(nav)

        # ---- 颜色选择器 ----
        self.picker = ColorSelector(two_rows=simple, size_hint_y=None)
        self.input_panel = None
        if simple:
            panel.add_widget(self.picker)
        else:
            panel_metrics = m.input_grid_metrics(3)
            self.input_panel = BoxLayout(
                orientation="vertical", size_hint_y=None,
                height=panel_metrics["height"], spacing=panel_metrics["spacing"][1])
            self.input_panel.add_widget(self.picker)

        # ---- 录入辅助工具（简洁模式隐藏）----
        self.controls_grid = GridLayout(
            cols=6, rows=2, size_hint_y=None, **m.input_grid_metrics(2))
        self.btn_pick = UIButton(text="" if not simple else tr("input.pick"),
                                 icon_name=None if simple else "pick")
        self.btn_pick.bind(on_release=lambda *a: self.toggle_pick())
        self.btn_fill = UIButton(text="" if not simple else tr("input.fill"),
                                 icon_name=None if simple else "fill")
        self.btn_fill.bind(on_release=lambda *a: self.fill_face())
        self.btn_undo = UIButton(text="" if not simple else tr("input.undo"),
                                 icon_name=None if simple else "undo")
        self.btn_undo.bind(on_release=lambda *a: self.undo())
        self.btn_redo = UIButton(text="" if not simple else tr("input.redo"),
                                 icon_name=None if simple else "redo")
        self.btn_redo.bind(on_release=lambda *a: self.redo())
        # ---- 打乱公式（简洁模式隐藏）----
        self.btn_scramble = UIButton(text="" if not simple else tr("input.scramble"),
                                     icon_name=None if simple else "scramble")
        self.btn_scramble.bind(on_release=lambda *a: self.open_scramble())


        # ---- 翻转导航 ----
        self.btn_prev = ArrowButton(direction="left", font_size="20sp")
        self.btn_prev.bind(on_release=lambda *a: self.prev_face())
        self.btn_next = ArrowButton(direction="right", font_size="20sp")
        self.btn_next.bind(on_release=lambda *a: self.next_face())

        # ---- Action buttons ----
        self.btn_twist = UIButton(text="" if not simple else tr("input.twist"),
                                  icon_name=None if simple else "twist")
        self.btn_twist.bind(on_release=lambda *a: self.open_twist())
        self.btn_random = UIButton(text="" if not simple else tr("input.random"),
                                   icon_name=None if simple else "random")
        self.btn_random.bind(on_release=lambda *a: self.random_load())
        self.btn_clear = DangerButton(text="" if not simple else tr("input.clear"),
                                      icon_name=None if simple else "clear")
        self.btn_clear.bind(on_release=lambda *a: self.confirm_clear())
        self.btn_check = UIButton(text="" if not simple else tr("input.check"),
                                  icon_name=None if simple else "check")
        self.btn_check.bind(on_release=lambda *a: self.check())
        self.btn_solve = PrimaryButton(text="", icon_name="solve")
        self.btn_solve.bind(on_release=lambda *a: self.start_solve())
        self.simple_turn_row = BoxLayout(
            size_hint_y=None, height=m.h(48), spacing=m.h(16),
            padding=[m.h(28), 0, m.h(28), 0])
        if simple:
            for b in (self.btn_prev, self.btn_solve, self.btn_next):
                self.simple_turn_row.add_widget(b)
            panel.add_widget(self.simple_turn_row)
        else:
            for b in (
                self.btn_pick, self.btn_fill, self.btn_undo, self.btn_redo,
                self.btn_prev, self.btn_next,
                self.btn_twist, self.btn_random, self.btn_clear,
                self.btn_solve, self.btn_check, self.btn_scramble,
            ):
                self.controls_grid.add_widget(b)
            self.input_panel.add_widget(self.controls_grid)
            panel.add_widget(self.input_panel)

        self.msg = Label(text="", size_hint_y=None, height=m.h(34),
                         color=(1, 0.55, 0.55, 1), halign="center")
        self.msg.bind(size=lambda widget, *_: setattr(widget, "text_size", widget.size))
        panel.add_widget(self.msg)
        root.set_content(self.view, panel)
        self._root_layout = root
        self._responsive_height_specs = [
            (top, 48), (nav, 48), (self.simple_turn_row, 48),
            (self.msg, 34),
        ]
        self.add_widget(root)
        # Refresh once the native window reports its final pixel height.
        Clock.schedule_once(lambda *_: self._apply_responsive_heights(), 0)

        if not getattr(self, "_resize_bound", False):
            self.bind(size=self._on_resize)
            self._resize_bound = True

    def apply_input_mode(self, simple):
        """切换高级/简洁输入：重建布局，保留已录入数据与朝向。"""
        if bool(getattr(self, "_simple", None)) == bool(simple):
            return
        self.reset_interaction()
        self.clear_widgets()
        self.build_ui()
        if getattr(self, "_ori", None) is not None:
            # 重建后是新视图，相机需重设为正对当前面（否则沿用默认斜视角，
            # 看起来魔方没有正对用户）。
            self.view.camera.elevation = 0.0
            self.view.camera.azimuth = 0.0
            self.view._display_zoom = 1.0
            self._refresh_view()
            self._update_turn_hints()
            self._update_face_label()

    def retranslate(self):
        """语言切换后重设静态文案。"""
        if not hasattr(self, "title"):
            return
        self.title.text = tr("input.title", n=self._n())
        self._update_turn_hints()
        self._update_progress()

    def _apply_responsive_heights(self):
        for widget, design_height in getattr(self, "_responsive_height_specs", ()):
            widget.height = m.h(design_height)
        if hasattr(self, "_root_layout"):
            pad = m.h(8)
            self._root_layout.padding = [pad, m.h(6), pad, pad]
            self._root_layout.spacing = m.h(8)
        if hasattr(self, "picker"):
            self.picker.update_metrics()
        if hasattr(self, "controls_grid"):
            for name, value in m.input_grid_metrics(2).items():
                setattr(self.controls_grid, name, value)
        if getattr(self, "input_panel", None) is not None:
            # Share one outer gutter and equal gaps across all three advanced rows.
            panel_metrics = m.input_grid_metrics(3)
            self.input_panel.height = panel_metrics["height"]
            self.input_panel.spacing = panel_metrics["spacing"][1]
            left, top, right, bottom = self.picker.padding
            self.picker.height -= bottom
            self.picker.padding = (left, top, right, 0)
            left, top, right, bottom = self.controls_grid.padding
            self.controls_grid.height -= top
            self.controls_grid.padding = (left, 0, right, bottom)
        if hasattr(self, "simple_turn_row"):
            self.simple_turn_row.padding = [m.h(28), 0, m.h(28), 0]
            self.simple_turn_row.spacing = m.h(16)

    def _on_resize(self, *args):
        self._apply_responsive_heights()
        Clock.schedule_once(lambda *a: self._refresh_view(), 0)

    def _init_for_n(self):
        self.reset_interaction()
        n = self._n()
        self._data = {f: [[""] * n for _ in range(n)] for f in FACES}
        self._ori = CubeOrientation(n)
        self.title.text = tr("input.title", n=n)
        self.btn_demo.disabled = n >= 6
        # 录入页相机正对当前面（+Z），不使用演示页的斜视角度。
        self.view.camera.elevation = 0.0
        self.view.camera.azimuth = 0.0
        self.view._display_zoom = 1.0
        self._reset_edits()
        self._error_cells.clear()
        self._refresh_view()
        self._update_progress()
        self._update_turn_hints()

    def _reset_edits(self):
        self._history = []
        self._redo = []
        self._drag_edits = {}
        self._pick_mode = False
        self.btn_pick.active = False
        self._update_edit_buttons()

    def _n(self):
        return _app().n

    # ---- 3D 视图 ----
    def _refresh_view(self):
        if not hasattr(self, "view"):
            return
        # set_cube() cancels the animation without calling its completion
        # callback. Release the screen lock too and restore the logical face.
        self._cancel_turn()
        facelets = self.collect_facelets()
        cube = _build_partial_cube(facelets, self._n())
        if cube is None:
            self.view.cube = None
            self.view._redraw()
            return
        highlighted = {
            pos_from_rc(self._n(), face, r, c)
            for face, r, c in self._error_cells
        }
        self.view.set_cube(cube, highlight=highlighted or None)
        self.view.set_whole_world(self._ori.world)
        self._update_face_label()

    def _update_face_label(self):
        face = self._ori.current_face()
        grid = self._data.get(face, [])
        face_done = sum(bool(col) for row in grid for col in row)
        filled = sum(bool(col) for cells in self._data.values()
                     for row in cells for col in row)
        if self._simple:
            self.face_label.text = tr(
                "input.face_progress", face=tr(f"face.{face}"), code=face,
                face_done=face_done, face_total=self._n() ** 2,
                done=filled, total=6 * self._n() ** 2)
        else:
            self.face_label.text = tr("input.face", face=tr(f"face.{face}"), code=face)

    def _update_progress(self):
        filled = sum(bool(col) for cells in self._data.values()
                     for row in cells for col in row)
        self.msg.text = tr("input.progress", done=filled, total=6 * self._n() ** 2)
        self.msg.color = _app().theme.text_muted
        self._update_face_label()

    def _find_piece_error_cells(self, facelets, n):
        if n not in (2, 3):
            return set()
        _d, maxc = get_d_maxc(n)
        centers = ({face: facelets[face][1][1] for face in FACES}
                   if n == 3 else DEFAULT_COLORS)
        cells = set()
        if n == 3:
            center_values = [centers[face] for face in FACES]
            if len(set(center_values)) != len(FACES):
                duplicates = {color for color in center_values
                              if center_values.count(color) > 1}
                return {(face, 1, 1) for face in FACES
                        if centers[face] in duplicates}
        values = coord_values(n)
        for x in values:
            for y in values:
                for z in values:
                    pos = (x, y, z)
                    outer_faces = []
                    for face in FACES:
                        normal = FACE_NORMALS[face]
                        axis = _axis_of(normal)
                        if pos[axis] == _sign(normal) * maxc:
                            outer_faces.append(face)
                    if len(outer_faces) != 3:
                        continue
                    actual = []
                    expected = []
                    for face in outer_faces:
                        r, c = rc_from_pos(n, face, pos)
                        actual.append(facelets[face][r][c])
                        expected.append(centers[face])
                    if sorted(actual) != sorted(expected):
                        for face in outer_faces:
                            r, c = rc_from_pos(n, face, pos)
                            cells.add((face, r, c))
        return cells

    def _focus_error_face(self):
        if not self._error_cells:
            return
        target = next(face for face in FACES
                      if any(error_face == face for error_face, _r, _c in self._error_cells))
        for _ in range(6):
            if self._ori.current_face() == target:
                break
            self._ori.turn_next()
        self._update_face_label()

    def _update_turn_hints(self):
        """上一步/下一步现在是自绘粗箭头（ArrowButton），无需设置文案。"""
        pass

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
                self.msg.text = tr("input.picked", col=col)
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
        self._error_cells.clear()
        self._valid = None
        if action is None:
            self._commit_action({(r, c): old})
        self._refresh_view()
        self._update_progress()

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
            self._error_cells.clear()
            self._valid = None
            self.msg.text = tr("input.filled", face=face, col=col)
        else:
            self.msg.text = tr("input.already", face=face, col=col)
        self._refresh_view()
        self._update_progress()

    def toggle_pick(self):
        self._pick_mode = not self._pick_mode
        self.btn_pick.active = self._pick_mode

    # ---- 撤销 / 重做 ----
    def undo(self):
        if not self._history:
            return
        action = self._history.pop()
        for face, r, c, old, _new in reversed(action):
            self._data[face][r][c] = old
        self._redo.append(action)
        self.msg.text = tr("input.undone")
        self._error_cells.clear()
        self._valid = None
        self._refresh_view()
        self._update_edit_buttons()
        self._update_progress()

    def redo(self):
        if not self._redo:
            return
        action = self._redo.pop()
        for face, r, c, _old, new in action:
            self._data[face][r][c] = new
        self._history.append(action)
        self.msg.text = tr("input.redone")
        self._error_cells.clear()
        self._valid = None
        self._refresh_view()
        self._update_edit_buttons()
        self._update_progress()

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

    def _cancel_turn(self):
        interrupted = self._busy_turn or self.view._whole_anim is not None
        self.view._cancel_whole_anim()
        self._pending_dir = None
        self._busy_turn = False
        if interrupted and self._ori is not None:
            self.view.set_whole_world(self._ori.world)

    def reset_interaction(self):
        """Keep entered colors, but release temporary touch and turn state."""
        self.view.cancel_touch()
        self._handle_drag_end()
        self._cancel_turn()
        self._pick_mode = False
        self.btn_pick.active = False

    def _after_turn(self):
        direction = self._pending_dir
        if direction not in ("prev", "next"):
            return
        if direction == "prev":
            self._ori.turn_prev()
        else:
            self._ori.turn_next()
        self._pending_dir = None
        self._busy_turn = False
        self.view.set_whole_world(self._ori.world)
        self._update_face_label()
        self._update_turn_hints()

    # ---- 数据存取 ----
    def collect_facelets(self):
        return {f: [row[:] for row in self._data.get(f, [])] for f in FACES}

    def set_facelets(self, facelets):
        self.reset_interaction()
        n = self._n()
        for f in FACES:
            if f in facelets:
                grid = facelets[f]
                self._data[f] = [[grid[r][c] for c in range(n)]
                                 for r in range(n)]
        self._reset_edits()
        self._error_cells.clear()
        self._refresh_view()
        self._update_progress()

    def on_cell(self, r, c, face):
        col = self.picker.current_color
        self._fill_cell(face, r, c, col)

    def random_load(self):
        from cube.conversion import cubies_to_facelets
        from cube.scramble import random_scramble
        import random as _random
        n = self._n()
        moves = random_scramble(n)
        if n == 3:
            # 3 阶固定中心在纯面转下不变；追加一次整体翻转，让六面中心色也变化
            # （解法端会按当前中心色重贴色，仍能解成六面纯色）。
            moves = moves + [_random.choice(["x", "x'", "y", "y'", "z", "z'"])]
        cube = _new_solved_cube(n)
        cube.apply_moves(moves)
        facelets = cubies_to_facelets(cube.cubies, n)
        self.set_facelets(facelets)
        self.msg.text = tr("input.random_loaded", k=len(moves))

    def open_scramble(self):
        """弹出输入框，让用户粘贴打乱公式（如 "R U R' U'"）。"""
        from kivy.uix.popup import Popup
        from kivy.uix.textinput import TextInput
        content = BoxLayout(orientation="vertical", spacing=12, padding=16)
        ti = TextInput(text="", multiline=False, size_hint_y=None, height=m.h(48),
                       hint_text=tr("input.scramble.hint"),
                       font_size="18sp")
        btns = BoxLayout(orientation="horizontal", spacing=8,
                         size_hint_y=None, height=m.h(52))
        cancel = UIButton(text="", icon_name="cancel")
        cancel.bind(on_release=lambda *a: popup.dismiss())
        ok = PrimaryButton(text="", icon_name="done")
        ok.bind(on_release=lambda *a: (self._apply_scramble_popup(ti.text),
                                       popup.dismiss()))
        btns.add_widget(cancel)
        btns.add_widget(ok)
        content.add_widget(ti)
        content.add_widget(btns)
        from ui.widgets.dialogs import theme_popup
        popup = Popup(title=tr("input.scramble"), content=content,
                      size_hint=(0.9, 0.34))
        theme_popup(popup, _app().theme)
        popup.open()

    def _apply_scramble_popup(self, text):
        self.load_scramble(text)

    def load_scramble(self, text):
        """解析打乱公式并载入对应状态；失败时在状态栏提示。返回是否成功。"""
        from cube.conversion import cubies_to_facelets
        from cube.scramble import text_to_moves
        n = self._n()
        try:
            moves, _skipped = text_to_moves(text, n)
        except ValueError as exc:
            self.msg.text = tr("input.scramble.error", tok=str(exc))
            return False
        if not moves:
            self.msg.text = tr("input.scramble.empty")
            return False
        cube = _new_solved_cube(n)
        try:
            cube.apply_moves(moves)
        except Exception:
            self.msg.text = tr("input.scramble.error", tok="?")
            return False
        self.set_facelets(cubies_to_facelets(cube.cubies, n))
        self.msg.text = tr("input.scramble.loaded", k=len(moves))
        return True

    def confirm_clear(self):
        from kivy.uix.popup import Popup
        content = BoxLayout(orientation="vertical", spacing=12, padding=16)
        label = Label(text=tr("input.clear.msg"), halign="center",
                      font_size="18sp", size_hint_y=1)
        btns = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=m.h(52))
        cancel = UIButton(text="", icon_name="cancel")
        cancel.bind(on_release=lambda *a: popup.dismiss())
        ok = DangerButton(text="", icon_name="clear")
        ok.bind(on_release=lambda *a: (self.clear_all(), popup.dismiss()))
        btns.add_widget(cancel)
        btns.add_widget(ok)
        content.add_widget(label)
        content.add_widget(btns)
        from ui.widgets.dialogs import theme_popup
        popup = Popup(title=tr("input.clear.title"), content=content, size_hint=(0.86, 0.34))
        theme_popup(popup, _app().theme)
        popup.bind(on_dismiss=lambda *a: None)
        popup.open()

    def clear_all(self):
        self.reset_interaction()
        n = self._n()
        for face in FACES:
            self._data[face] = [[""] * n for _ in range(n)]
        self._ori = CubeOrientation(n)
        self._busy_turn = False
        self._pending_dir = None
        self._reset_edits()
        self._error_cells.clear()
        self._valid = None
        self._refresh_view()
        self.msg.text = tr("input.cleared")

    def reset_all(self):
        self._init_for_n()

    def on_enter(self):
        self.reset_interaction()
        n = self._n()
        cur_simple = bool(getattr(_app(), "simple_input", False))
        if getattr(self, "_simple", None) != cur_simple:
            self.apply_input_mode(cur_simple)
        self.title.text = tr("input.title", n=n)
        if not self._initialized or getattr(self, "_n_for_screen", None) != n:
            self._init_for_n()
            self._n_for_screen = n
            self._initialized = True
        self.btn_demo.disabled = n >= 6
        self.btn_demo.opacity = 0 if n >= 6 else 1
        # 5 阶专属重资源在用户填色期间后台预热，避免启动时无谓开销。
        if n == 5:
            try:
                from app.warmup import warmup_5x5
                warmup_5x5()
            except Exception:
                pass
        app = _app()
        if app.facelets_input is not None:
            self.set_facelets(app.facelets_input)
            self.msg.text = tr("input.resumed")
        else:
            self._refresh_view()

    def on_pre_leave(self, *args):
        self.reset_interaction()

    # ---- 校验 ----
    def check(self):
        facelets = self.collect_facelets()
        n = self._n()
        self._error_cells.clear()
        empty = []
        for face in FACES:
            for r in range(n):
                for c in range(n):
                    if not facelets[face][r][c]:
                        empty.append(f"{tr('face.' + face)} {r + 1},{c + 1}")
                        self._error_cells.add((face, r, c))
        if empty:
            self.msg.text = tr("input.missing", list=", ".join(empty[:8]))
            self.msg.color = _app().theme.danger
            self._valid = False
            self._focus_error_face()
            self._refresh_view()
            return
        lang = current_language()
        if n == 2:
            errs = validate_2x2(facelets, lang=lang)
        elif n == 3:
            errs = validate_3x3(facelets, lang=lang)
        elif n == 5:
            errs = validate_5x5(facelets, lang=lang)
        elif n >= 6:
            from cube.validation_n import validate_nxn
            errs = validate_nxn(facelets, n, lang=lang)
        else:
            errs = validate_4x4(facelets, lang=lang)
        if errs:
            counts = {}
            self._error_cells.update(self._find_piece_error_cells(facelets, n))
            for face in FACES:
                for row in facelets[face]:
                    for col in row:
                        counts[col] = counts.get(col, 0) + 1
            overrepresented = {
                col for col, count in counts.items() if count > n * n
            }
            for face in FACES:
                for r, row in enumerate(facelets[face]):
                    for c, col in enumerate(row):
                        if col in overrepresented:
                            self._error_cells.add((face, r, c))
            self.msg.text = errs[0]
            self.msg.color = _app().theme.danger
            self._valid = False
            if self._error_cells:
                self._focus_error_face()
                self._refresh_view()
            return
        self.msg.text = tr("input.valid")
        self.msg.color = _app().theme.accent
        self._valid = True
        self._refresh_view()

    def start_solve(self):
        self.check()
        if not getattr(self, "_valid", False):
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
            # 惰性导入：solver4 -> solver3（kociemba 表 ~7s），避免启动首帧前加载。
            from solver.solver4 import _rebuild_center_homes
            _rebuild_center_homes(cubies)
        app.set_cube(cubies, self._n())
        app.facelets_input = facelets

    def go_home(self):
        self.manager.current = "HomeScreen"

    def open_demo(self):
        if self._n() >= 6:
            return
        app = _app()
        app.facelets_input = self.collect_facelets()
        menu = self.manager.get_screen("DemoMenuScreen")
        menu.set_mode(self._n())
        self.manager.current = "DemoMenuScreen"

    def open_twist(self):
        self.manager.current = "TwistScreen"


def _app():
    from kivy.app import App
    return App.get_running_app()
