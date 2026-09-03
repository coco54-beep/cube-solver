"""录入页：展开图输入 + 颜色选择 + 校验 + 求解。"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.screenmanager import Screen


class PrimaryButton(Button):
    """主操作按钮（绿色主题，见 app.kv 的 <PrimaryButton> 规则）。"""
    pass


class DangerButton(Button):
    """危险操作按钮（红色主题，见 app.kv 的 <DangerButton> 规则）。"""
    pass

from app.constants import FACE_LABEL, FACES
from cube.conversion import facelets_to_cubies, cubies_to_facelets
from cube.cubie_model import Cubie
from cube.coordinates import FACE_NORMALS, pos_from_rc, get_d_maxc, coord_values, rc_from_pos
from cube.validation import validate_3x3, validate_4x4
from cube.cube4 import Cube4
from cube.cube3 import Cube3
from ui.widgets.face_grid import FaceGrid
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
    return Cube4(cubies) if n == 4 else Cube3(cubies)


class InputScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
        self.reset_all()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=14, padding=[10, 6, 10, 10])

        # ---- 顶栏 ----
        top = BoxLayout(size_hint_y=None, height=46, spacing=8)
        back = Button(text="←返回", size_hint_x=0.22)
        back.bind(on_release=lambda *a: self.go_home())
        self.title = Label(text="录入 4x4", size_hint_x=0.78, halign="center",
                           font_size="20sp", bold=True)
        top.add_widget(back)
        top.add_widget(self.title)
        root.add_widget(top)

        # ---- 主显示区：展开图（十字布局）居中占满 ----
        # 用 AnchorLayout 让展开图在可用区域内居中，避免 ScrollView 左上对齐留白。
        self.center_grid = AnchorLayout(size_hint=(1.0, 1.0))
        self.grid_cross = BoxLayout(orientation="vertical", spacing=8,
                                    size_hint=(None, None))
        self._top_row = BoxLayout(orientation="horizontal", spacing=8,
                                  size_hint=(None, None))
        self._mid_row = BoxLayout(orientation="horizontal", spacing=8,
                                  size_hint=(None, None))
        self._bottom_row = BoxLayout(orientation="horizontal", spacing=8,
                                     size_hint=(None, None))
        self.grid_cross.add_widget(self._top_row)
        self.grid_cross.add_widget(self._mid_row)
        self.grid_cross.add_widget(self._bottom_row)
        self.center_grid.add_widget(self.grid_cross)
        root.add_widget(self.center_grid)

        # ---- 颜色选择器 ----
        self.picker = ColorSelector(size_hint_y=None, height=60)
        self.picker.bind(on_select=lambda *a: self._sync_grid_colors())
        root.add_widget(self.picker)

        # ---- 操作按钮行 ----
        action_row = BoxLayout(size_hint_y=None, height=60, spacing=8)
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
        self.msg = Label(text="", size_hint_y=None, height=36,
                         color=(1, 0.55, 0.55, 1), halign="center")
        root.add_widget(self.msg)
        self.add_widget(root)

        # 展开图占满显示区
        self.center_grid.size_hint = (1, 1)
        self.bind(size=self._reflow)

    # ---- 初始化网格 ----
    def _fit_cell(self, n):
        """根据可用显示区宽高计算格子尺寸，使展开图尽可能铺满且不超屏。

        十字布局：中排 4 个面最宽，纵向 3 排最高。用最小值保证不溢出，
        再限制在 [16, 46] 之间，兼容 3 阶 / 4 阶与不同分辨率。
        """
        from kivy.core.window import Window
        width = self.width if self.width > 1 else Window.width
        height = self.height if self.height > 1 else Window.height
        # 扣除顶栏与控制区（含颜色选择行、按钮行、消息、间距、padding）的估算高度
        controls_h = 46 + 60 + 60 + 36 + 48
        avail_w = max(1.0, width - 2 * 10 - 8)
        avail_h = max(1.0, height - controls_h)
        cell_w = (avail_w - 3 * 8) / (4.0 * n)
        cell_h = (avail_h - 2 * 8) / (3.0 * n)
        cell = int(min(cell_w, cell_h, 46))
        return max(16, cell)

    def _reflow(self, *args):
        """屏幕尺寸变化时重建展开图，并保留已录入的颜色。"""
        from kivy.clock import Clock
        Clock.schedule_once(self._do_reflow, 0)

    def _do_reflow(self, *dt):
        if not hasattr(self, "_grids"):
            return
        data = None
        try:
            data = self.collect_facelets()
        except Exception:
            data = None
        self.reset_all()
        if data:
            self.set_facelets(data)

    def reset_all(self):
        n = self._n()
        # 清掉旧的 FaceGrid（标准十字布局）
        self._top_row.clear_widgets()
        self._mid_row.clear_widgets()
        self._bottom_row.clear_widgets()
        self._grids = {}
        cell = self._fit_cell(n)
        fw = n * cell                 # 单个网格宽/高（无标签）
        gw = 4 * fw + 3 * 8           # 中排 4 格宽 + spacing
        gh = 3 * fw + 2 * 8           # 3 排高 + spacing
        # 中排 4 个面：L F R B（按相邻接触顺序 L-F、F-R、R-B，从左到右）
        for face in ("L", "F", "R", "B"):
            fg = FaceGrid(face=face, size_n=n, cell_size=cell,
                          show_labels=False, on_change=self.on_grid_change)
            self._mid_row.add_widget(fg)
            self._grids[face] = fg
        # 顶排 U、底排 D：spacing=0，spacer(宽=L宽+spacing) 使 U/D 左缘= F 左缘
        self._top_row.spacing = 0
        self._bottom_row.spacing = 0
        spacer = fw + 8
        for face, row in (("U", self._top_row), ("D", self._bottom_row)):
            sp = BoxLayout(size_hint_x=None, width=spacer)
            row.add_widget(sp)
            fg = FaceGrid(face=face, size_n=n, cell_size=cell,
                          show_labels=False, on_change=self.on_grid_change)
            row.add_widget(fg)
            self._grids[face] = fg
        # 顶/底排宽度 = 中排宽度（U/D 左缘对齐 F 左缘）
        for row in (self._top_row, self._mid_row, self._bottom_row):
            row.size_hint = (None, None)
            row.size = (gw, fw)
        self.grid_cross.size = (max(gw, fw), gh)
        self.grid_cross.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        # 同步当前选中颜色到网格
        self._sync_grid_colors()

    def _sync_grid_colors(self):
        """把颜色选择器的当前色同步到所有网格，点击格子用该颜色。"""
        col = self.picker.current_color
        for g in self._grids.values():
            g.set_color(col)

    def on_grid_change(self):
        self.msg.text = ""

    def _n(self):
        app = _app()
        return app.n

    # ---- 数据存取 ----
    def collect_facelets(self):
        return {f: g.get_grid() for f, g in self._grids.items()}

    def set_facelets(self, facelets):
        for f in FACES:
            if f in facelets:
                self._grids[f].set_grid(facelets[f])

    def random_load(self):
        """随机打乱一个该阶的已还原魔方，填充展开图（方便测试破解）。

        随机生成若干基础/宽层动作，从 solved 应用得到随机状态，
        转成 facelets 填充各面网格并同步 3D 视图。
        """
        import random
        from cube.cube4 import Cube4
        from cube.cube3 import Cube3
        from cube.conversion import cubies_to_facelets
        n = self._n()
        cube = Cube4.solved() if n == 4 else Cube3.solved()
        faces = ["U", "D", "F", "B", "R", "L", "u", "d", "f", "b", "r", "l"] if n == 4 \
            else ["U", "D", "F", "B", "R", "L"]
        suff = ["", "'", "2"]
        moves = [random.choice(faces) + random.choice(suff)
                 for _ in range(random.randint(12, 25))]
        cube.apply_moves(moves)
        facelets = cubies_to_facelets(cube.cubies, n)
        self.set_facelets(facelets)
        self.msg.text = f"已加载随机布局（{len(moves)} 步打乱）"

    def confirm_clear(self):
        """清空操作前二次确认。"""
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
        for face in FACES:
            grid = [[""] * self._n() for _ in range(self._n())]
            self._grids[face].set_grid(grid)
        self.msg.text = "已清空"

    def on_enter(self):
        app = _app()
        name = "粽子魔方" if app.puzzle == "mastermorphix" else f"{self._n()}x{self._n()}"
        self.title.text = f"录入 {name}"
        self.reset_all()
        # 从回放/求解返回时，自动恢复上次布局，减少重复录入
        app = _app()
        if app.facelets_input is not None:
            self.set_facelets(app.facelets_input)
            self.msg.text = "已加载上次布局，直接点「开始求解」可沿用上次方案"

    # ---- 校验 ----
    def check(self):
        facelets = self.collect_facelets()
        n = self._n()
        # 空格检查
        empty = []
        for face in FACES:
            for r in range(n):
                for c in range(n):
                    if not facelets[face][r][c]:
                        empty.append(f"{FACE_LABEL[face]}{r+1}{c+1}")
        if empty:
            self.msg.text = f"未填写: {','.join(empty[:8])}"
            return
        errs = validate_3x3(facelets) if n == 3 else validate_4x4(facelets)
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
        # 布局与上次一致且有上次方案：直接复用，跳过重新求解
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

    def on_cell(self, r, c, face):
        col = self.picker.current_color
        self._grids[face]._data[(r, c)] = col
        self._grids[face]._paint(r, c, col)
        self.msg.text = ""

    def go_home(self):
        self.manager.current = "HomeScreen"


def _app():
    from kivy.app import App
    return App.get_running_app()
