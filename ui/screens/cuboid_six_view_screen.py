"""Production six-view entry for shape-changing cuboids and Camouflage."""
import threading
from copy import deepcopy
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from cube.cuboid_observation import SixViewDraft, MatchResult, FACE_ORDER, UNKNOWN, EMPTY, PLASTIC
from cube.cuboid import FACES, CuboidCube
from app.i18n import tr
from app.prefs import get as pref_get, set as pref_set
from renderer.polyhedral_view import default_palette
from ui.screens.entry_mixin import EntryActionsMixin
from ui.screens.mastermorphix_screen import _Swatch
from ui.widgets.six_view_grid import SixViewGrid
from ui.widgets.buttons import UIButton, PrimaryButton, DangerButton
from ui.widgets.layouts import ResponsiveBoxLayout, AdaptiveSceneLayout
from ui.widgets import metrics as m


def _app():
    return App.get_running_app()


def cube_key(cube):
    return cube.puzzle_kind, tuple(cube.frames), tuple(cube.colors)


class CuboidSixViewScreen(EntryActionsMixin, Screen):
    entry_twist_screen = 'PolyhedralTwistScreen'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cube = None; self._draft = None; self._six_state = None; self._six_face = 2
        self._six_undo = []; self._six_applied = None; self._six_cube_key = None
        self._job = None; self._cancel = threading.Event(); self._color = 0; self._depth = None
        self._message = ''; self._selected = (); self._after_match = None
        self._build()

    def _button(self, row, icon, callback, cls=UIButton, text=''):
        button = cls(icon_name=icon, text=text, font_size='13sp')
        button.bind(on_release=lambda *_: callback())
        row.add_widget(button); return button

    def _build(self):
        root = AdaptiveSceneLayout(gap_px=6)
        self._root_layout = root
        top = ResponsiveBoxLayout(height_px=44, gap_px=8)
        self._button(top, 'back', self.back).size_hint_x = .2
        self.title = Label(font_size='18sp'); top.add_widget(self.title)
        self._button(top, 'demo', self.help).size_hint_x = .2
        root.add_widget(top)
        scene = ResponsiveBoxLayout(orientation='vertical', gap_px=4)
        self.face_label = Label(size_hint_y=None, height=m.h(28), font_size='15sp')
        scene.add_widget(self.face_label)
        self.grid = SixViewGrid(); self.grid.on_region = self.select_region
        scene.add_widget(self.grid)
        self.reference = Label(size_hint_y=None, height=m.h(42), font_size='12sp', halign='center', valign='middle')
        self.reference.bind(size=lambda w, *_: setattr(w, 'text_size', w.size)); scene.add_widget(self.reference)
        panel = ResponsiveBoxLayout(orientation='vertical', gap_px=6, size_hint_y=None)
        tabs = ResponsiveBoxLayout(height_px=42, gap_px=4); self.tabs = {}
        for face in FACE_ORDER:
            self.tabs[face] = self._button(tabs, '', lambda f=face: self.change_face(f))
        panel.add_widget(tabs)
        hint = Label(text=tr('six.draw_hint'), size_hint_y=None, height=m.h(40), font_size='12sp', halign='center', valign='middle')
        hint.bind(size=lambda w, *_: setattr(w, 'text_size', w.size)); self.hint = hint; panel.add_widget(hint)
        self.colors = GridLayout(cols=6, spacing=m.h(5), size_hint_y=None, height=m.h(42)); panel.add_widget(self.colors)
        row = ResponsiveBoxLayout(height_px=40, gap_px=5)
        self.tools = {}
        for color, key in ((EMPTY, 'six.empty'), (PLASTIC, 'six.plastic'), (UNKNOWN, 'six.unknown')):
            self.tools[color] = self._button(row, '', lambda c=color: self.select_color(c), text=tr(key))
        panel.add_widget(row)
        row = ResponsiveBoxLayout(height_px=38, gap_px=5)
        self._button(row, 'prev', lambda: self.change_depth(-1)).size_hint_x = .28
        self.depth_label = self._button(row, '', self.auto_depth); row.children[0].size_hint_x = 1
        self._button(row, 'next', lambda: self.change_depth(1)).size_hint_x = .28
        panel.add_widget(row)
        row = ResponsiveBoxLayout(height_px=40, gap_px=5)
        self.outside_button = self._button(row, '', self.complete_face, text=tr('six.outside'))
        self._button(row, 'next', self.next_face).size_hint_x = .35
        panel.add_widget(row)
        row = ResponsiveBoxLayout(height_px=44, gap_px=5)
        self._button(row, 'undo', self.undo)
        self._button(row, 'clear', self.clear_face, DangerButton)
        self._button(row, 'gear', self.open_palette_settings)
        self.apply_button = self._button(row, 'check', self.apply, PrimaryButton)
        self._button(row, 'cancel', self.cancel_matching)
        panel.add_widget(row)
        row = ResponsiveBoxLayout(height_px=44, gap_px=5)
        self.twist_button = self._button(row, 'twist', self.open_twist)
        self._button(row, 'random', self.randomize)
        self._button(row, 'target', self.assign_initial)
        self.solve_button = self._button(row, 'solve', self.solve, PrimaryButton)
        panel.add_widget(row)
        self.status = Label(size_hint_y=None, height=m.h(54), font_size='12sp', halign='center', valign='middle')
        self.status.bind(size=lambda w, *_: setattr(w, 'text_size', w.size)); panel.add_widget(self.status)
        root.set_content(scene, panel); self.add_widget(root)

    def on_pre_enter(self, *args):
        cube = _app().cube
        if not getattr(cube, 'can_change_shape', False):
            Clock.schedule_once(lambda *_: setattr(self.manager, 'current', 'PolyhedralScreen'), 0); return
        current_key = cube_key(cube)
        keep = self._six_state is not None and self._six_state.get('kind') == cube.puzzle_kind
        if keep:
            keep = self._six_state.get('version') == (2 if getattr(cube, 'panel_anchored', False) else 1)
        if not keep or (self._six_cube_key is not None and self._six_cube_key != current_key):
            if not keep or self._cube is not cube:
                self._six_undo = []
            self._six_face = 2; self._six_applied = None
            if all(c >= 0 for c in cube.colors):
                draft = SixViewDraft.from_cube(cube); self._six_applied = draft.state()
            else:
                draft = SixViewDraft(cube.puzzle_kind)
            self._six_state = draft.state()
        self._cube = cube; self._six_cube_key = current_key
        self._depth = None; self._selected = ()
        self._draft = SixViewDraft(cube.puzzle_kind, self._six_state)
        self.palette = tuple(tuple(c) for c in pref_get('poly_palette_'+cube.puzzle_kind, default_palette(cube)))
        self._build_colors(); self.retranslate(); self._refresh()
        Clock.schedule_once(self._settle_layout, 0)

    def _settle_layout(self, *_):
        # Colours are populated after the initial ScreenManager construction.
        self._root_layout._adapt()

    def _build_colors(self):
        self.colors.clear_widgets(); self._swatches = []
        for color in range(6):
            button = _Swatch(self.palette[color], text=str(color+1), active=color == self._color)
            button.bind(on_release=lambda *_, c=color: self.select_color(c))
            self.colors.add_widget(button); self._swatches.append(button)

    def _remember(self, cube=False):
        self._six_undo.append((deepcopy(self._six_state), self._six_face,
                               self._cube.clone() if cube else None, deepcopy(self._six_applied)))
        self._six_undo = self._six_undo[-40:]

    def _sync(self):
        self._six_state = self._draft.state(); self._message = ''
        _app().polyhedral_solution = None; self._refresh()

    def _refresh(self):
        if self._draft is None:
            return
        face = self._six_face
        self.title.text = tr('directory.'+self._draft.kind)+' · '+tr('six.title')
        self.face_label.text = tr('input.face', face=tr('face.'+FACES[face]), code=FACES[face])
        top = ('B','U','U','F','U','U')[face]
        right = ('R','B','R','R','F','L')[face]
        self.reference.text = tr('six.face_reference', top=tr('face.'+top), right=tr('face.'+right))
        self.grid.set_draft(self._draft, face, self.palette); self.grid.selection = self._selected; self.grid.redraw()
        for f, button in self.tabs.items():
            button.text = tr('face.'+FACES[f]); button.active = f == face
        for i, button in enumerate(self._swatches):
            button.active = i == self._color
        for color, button in self.tools.items():
            button.active = color == self._color
        self.depth_label.text = tr('six.depth_auto') if self._depth is None else tr('six.depth_level', n=self._draft.model['levels'][face].index(self._depth)+1)
        complete = sum(all(c != UNKNOWN for c, _, _ in view) for view in self._draft.views)
        self.status.text = self._message or tr('six.progress', n=complete)
        self.apply_button.disabled = self._job is not None
        self.grid.disabled = self._job is not None

    def change_face(self, face):
        if self._job is not None:
            return
        self._six_face = face; self._selected = (); self._depth = None; self._refresh()

    def next_face(self):
        self.change_face(FACE_ORDER[(FACE_ORDER.index(self._six_face)+1) % 6])

    def select_color(self, color):
        if self._job is None:
            self._color = color; self._refresh()

    def select_region(self, indices):
        if self._job is not None or not indices:
            return
        self._remember(); self._selected = indices
        self._draft.paint(self._six_face, indices, self._color, self._depth); self._sync()

    def change_depth(self, delta):
        if self._job is not None:
            return
        levels = self._draft.model['levels'][self._six_face]
        index = -1 if self._depth is None else levels.index(self._depth)
        self._depth = levels[max(0, min(len(levels)-1, index+delta))]
        self._set_selected_depth()

    def auto_depth(self):
        if self._job is None:
            self._depth = None; self._set_selected_depth()

    def _set_selected_depth(self):
        if self._selected:
            self._remember()
            for i in self._selected:
                color, group, _ = self._draft.views[self._six_face][i]
                if color not in (EMPTY, UNKNOWN):
                    self._draft.views[self._six_face][i] = (color, group, self._depth)
            self._sync()
        else:
            self._refresh()

    def complete_face(self):
        if self._job is None:
            self._remember(); self._draft.mark_outside(self._six_face); self._sync()

    def clear_face(self):
        if self._job is None:
            self._remember()
            self._draft.paint(self._six_face, range(len(self._draft.views[self._six_face])), UNKNOWN)
            self._selected = (); self._sync()

    def undo(self):
        if self._job is None and self._six_undo:
            state, self._six_face, previous, self._six_applied = self._six_undo.pop()
            if previous is not None:
                self._cube.restore(previous); self._six_cube_key = cube_key(self._cube)
            self._depth = None
            self._draft = SixViewDraft(self._cube.puzzle_kind, state); self._selected = (); self._sync()

    def _load_cube(self, cube):
        self._remember(cube=True); self._cube.restore(cube); _app().cube = self._cube
        self._six_cube_key = cube_key(self._cube)
        self._draft = SixViewDraft.from_cube(self._cube); self._six_applied = self._draft.state()
        self._selected = (); self._sync()

    def remember_twist(self, previous):
        self._six_undo.append((deepcopy(self._six_state), self._six_face,
                               previous.clone(), deepcopy(self._six_applied)))
        self._six_undo = self._six_undo[-40:]

    def randomize(self):
        if self._job is None:
            from cube.polyhedral_scramble import scramble, scramble_length
            cube = CuboidCube.solved(self._cube.puzzle_kind)
            scramble(cube, scramble_length(cube)); self._load_cube(cube)

    def entry_can_assign(self):
        return self._cube is not None and self._job is None

    def entry_reset_solved(self):
        self._load_cube(CuboidCube.solved(self._cube.puzzle_kind))

    def entry_commit_state(self):
        _app().cube = self._cube; _app().polyhedral_solution = None

    def entry_set_status(self, text, error=False):
        self._message = text; self._refresh()

    def _ready(self):
        return self._six_applied == self._six_state

    def open_twist(self):
        if self._job is None:
            self._match('twist')

    def solve(self):
        if self._job is None:
            self._match('solve')

    def apply(self):
        if self._job is None:
            self._match(None)

    def _match(self, after):
        if self._ready():
            self._continue(after); return
        missing = self._draft.missing()
        if missing:
            self._six_face, cell = missing; self._selected = (cell,)
            self._depth = None
            self._message = tr('six.incomplete'); self._refresh(); return
        draft = SixViewDraft(self._draft.kind, deepcopy(self._six_state))
        self._cancel = threading.Event(); token = self._cancel; self._job = token
        self._message = tr('six.matching'); self._refresh()
        def work():
            try:
                result = draft.match(cancel=token)
            except Exception:
                from kivy.logger import Logger
                Logger.exception('Six-view matching failed')
                result = MatchResult('error')
            Clock.schedule_once(lambda *_: self._matched(token, result, after), 0)
        threading.Thread(target=work, daemon=True).start()

    def _matched(self, token, result, after):
        if self._job is not token:
            return
        self._job = None
        if result.status == 'ok':
            self._cube.restore(result.cube); self._six_cube_key = cube_key(self._cube)
            self._six_applied = deepcopy(self._six_state)
            _app().cube = self._cube; _app().polyhedral_solution = None
        elif result.face is not None:
            self._six_face = result.face; self._selected = (result.cell,)
            self._depth = None
        self._message = tr('six.'+result.status); self._refresh()
        if result.status == 'ok':
            self._continue(after)

    def _continue(self, after):
        if after == 'twist':
            self.manager.current = 'PolyhedralTwistScreen'
        elif after == 'solve':
            entered = self._cube.entered(); palette = self.palette
            def solved(result):
                _app().polyhedral_solution = (entered, result.moves, palette)
                self.manager.current = 'PolyhedralPlaybackScreen'
            from renderer.cuboid_view import CuboidView
            self.manager.get_screen('SolvingScreen').configure(entered, self.name, solved, CuboidView, palette)
            self.manager.current = 'SolvingScreen'

    def cancel_matching(self):
        if self._job is not None:
            self._cancel.set(); self._job = None
            self._message = tr('six.cancelled'); self._refresh()

    def reset_interaction(self):
        self.grid.cancel_touch(); self.cancel_matching()

    def on_pre_leave(self, *args):
        self.reset_interaction()

    def back(self):
        self.reset_interaction()
        self.manager.current = 'CameraScreen' if getattr(_app(), 'input_from_camera', False) else 'HomeScreen'

    def help(self):
        from kivy.uix.popup import Popup
        from ui.widgets.dialogs import theme_popup
        label = Label(text=tr('six.help'), halign='left', valign='middle', font_size='14sp')
        label.bind(size=lambda w, *_: setattr(w, 'text_size', (w.width-m.h(24), w.height)))
        popup = Popup(title=tr('six.title'), content=label, size_hint=(.9, .75))
        theme_popup(popup, _app().theme); popup.open()

    def retranslate(self):
        self.hint.text = tr('six.draw_hint')
        self.outside_button.text = tr('six.outside')
        for color, key in ((EMPTY, 'six.empty'), (PLASTIC, 'six.plastic'), (UNKNOWN, 'six.unknown')):
            self.tools[color].text = tr(key)
        self._refresh()

    def refresh_theme(self):
        self.grid.redraw()

    def palette_colors(self):
        return list(self.palette)

    def default_palette_colors(self):
        return list(default_palette(self._cube))

    def palette_title(self):
        return tr('directory.'+self._cube.puzzle_kind)

    def apply_palette_colors(self, colors):
        self.palette = tuple(tuple(c) for c in colors)
        pref_set('poly_palette_'+self._cube.puzzle_kind, [list(c) for c in colors])
        self._build_colors(); self._refresh()

    def open_palette_settings(self):
        if self._job is None and self._cube is not None:
            self.manager.get_screen('PiecePaletteScreen').configure(self, max(0, self._color))
            self.manager.current = 'PiecePaletteScreen'
