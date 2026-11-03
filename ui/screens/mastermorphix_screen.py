"""Piece input for a scrambled Mastermorphix, including shape/orientation."""
from ui.entry_feedback import validation_action

import math
from kivy.uix.screenmanager import Screen
from ui.screens.entry_mixin import EntryActionsMixin
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from ui.widgets.entry_guidance import EntryGuidance
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

from app.constants import COLOR_INFO
from app.i18n import tr
from app.mastermorphix_palette import save_palette
from cube.mastermorphix import (MastermorphixCube, DEFAULT_PALETTE, POSITIONS, positions_for_order, AXIS_FACES, position_kind, position_name,
                               placements, make_piece, piece_colors, equivalent_placements,
                               normalize_input, MorphixInputError)
from cube.coordinates import FACE_NORMALS
from renderer.mastermorphix_view import MastermorphixView
from renderer.cube_orientation import CubeOrientation
from ui.widgets.buttons import UIButton, PrimaryButton, DangerButton
from ui.widgets.layouts import ResponsiveBoxLayout,AdaptiveSceneLayout
from ui.widgets import metrics as m
from ui.widgets.dialogs import theme_popup
from ui.widgets.camera_follow import CameraFollowControl
from ui.widgets.entry_controls import (entry_header, entry_actions, EntryGalleryPager,
                                      GALLERY_COLUMNS, GALLERY_PAGE_SIZE)


def _app():
    from kivy.app import App
    return App.get_running_app()


class _Swatch(UIButton):
    def __init__(self, rgba, **kwargs):
        self.rgba = rgba
        super().__init__(**kwargs)
        self.color = (0.04, .07, .1, 1) if sum(rgba[:3]) > 1.5 else (1, 1, 1, 1)

    def _button_color(self):
        return self.rgba

    def _pressed_color(self):
        return tuple(c*.8 for c in self.rgba[:3]) + (1,)


def _thumbnail_camera_for(view, pos):
    """Orient only the shape cards; selection never moves the main camera."""
    x, y, z = pos
    view.camera.azimuth = math.degrees(math.atan2(x, z))
    view.camera.elevation = math.degrees(math.atan2(y, max(.05, math.hypot(x, z))))
    # An axis view is slightly tilted so both colored sides of its center show.
    if position_kind(pos) == "center":
        view.camera.elevation = max(-70, min(70, view.camera.elevation + 12))
        view.camera.azimuth += 15
    view._redraw()


class MastermorphixScreen(EntryActionsMixin, Screen):
    supports_palette_settings=True
    reference_height_px=24
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cube = None
        self._recorded = set()
        self._history = []
        self._gallery_page = 0
        self._group = "center"
        self._pos = (0, 1, 0)
        self._preview = None
        self._ori = CubeOrientation(3)
        self._busy_turn = False
        self._pending_dir = None
        self.build_ui()

    def build_ui(self):
        root = AdaptiveSceneLayout()
        self._root_layout = root
        self.title = Label(text=tr("morphix.title"), font_size="20sp", bold=True)
        top, self.btn_back, self.demo_button = entry_header(self.title, self.go_back, self.open_demo)
        self.palette_button=UIButton(icon_name='gear')
        self.palette_button.bind(on_release=lambda *_:self.open_palette_settings())
        root.add_widget(top)
        # Kept for subclass compatibility; palette editing lives on its own page.
        self.palette_row = ResponsiveBoxLayout(height_px=0, gap_px=8)
        self.reference_label = Label(size_hint_y=None, height=m.h(self.reference_height_px), font_size="12sp", halign="center")
        self.view = MastermorphixView()
        # CubeOrientation aligns each observation axis with +Z. Use the same
        # straight-on camera as advanced input, rather than CubeView's tilt.
        self.view.camera.azimuth = 0.0
        self.view.camera.elevation = 0.0
        self.view.lock_rotation = True
        self.view.show_axes = True
        self.view.on_pick_piece = self.select_position
        controls = ResponsiveBoxLayout(orientation="vertical", gap_px=6, size_hint_y=None)
        controls.bind(minimum_height=controls.setter("height"))
        self._controls = controls
        controls.add_widget(self.reference_label)
        self.slot = Label(size_hint_y=None, height=m.h(28), font_size="14sp")
        controls.add_widget(self.slot)
        self.gallery = GridLayout(cols=GALLERY_COLUMNS, size_hint_y=None, height=m.h(66), spacing=m.h(6))
        controls.add_widget(self.gallery)
        self.gallery_pages = EntryGalleryPager(self._change_gallery_page)
        self.gallery_page_label = self.gallery_pages.label
        self.gallery_page_prev = self.gallery_pages.previous
        self.gallery_page_next = self.gallery_pages.next
        controls.add_widget(self.gallery_pages)
        navigation = ResponsiveBoxLayout(height_px=44, gap_px=6)
        self.navigation = navigation
        self.btn_prev = UIButton(icon_name="prev")
        self.btn_prev.bind(on_release=lambda *_: self.turn_view(-1))
        self.rotate = UIButton(icon_name="reset")
        self.rotate.bind(on_release=lambda *_: self.rotate_piece())
        self.btn_next = UIButton(icon_name="next")
        self.btn_next.bind(on_release=lambda *_: self.turn_view(1))
        for button in (self.btn_prev, self.palette_button, self.rotate, self.btn_next):
            if button is self.palette_button and not self.supports_palette_settings:
                continue
            navigation.add_widget(button)
        controls.add_widget(navigation)
        self.hint = EntryGuidance(text=tr("morphix.hint"), size_hint_y=None, height=m.h(44),
                          font_size="12sp", halign="center", valign="middle")
        self.hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        controls.add_widget(self.hint)
        actions, self.entry_action_buttons = entry_actions(twist=self.open_twist,
            randomize=self.random_load, clear=self.confirm_clear, undo=self.undo,
            assign=self.assign_initial, solve=self.start_solve)
        controls.add_widget(actions)
        self.progress = Label(size_hint_y=None, height=m.h(24), font_size="13sp")
        controls.add_widget(self.progress)
        self.follow_control=CameraFollowControl()
        self.follow_control.bind_view(self.view)
        controls.add_widget(self.follow_control)
        root.set_content(self.view,controls)
        self.main=root.body
        self._controls_scroll=root.panel_viewport
        self.add_widget(root)
        self.bind(size=lambda *_: self._resize())
        controls.bind(minimum_height=lambda *_: self._resize())

    def _resize(self):
        rows = max(1, (len(self.gallery.children) + self.gallery.cols - 1) // self.gallery.cols)
        self.gallery.height = rows*m.h(66) + (rows-1)*m.h(6)
        self.gallery.spacing = m.h(6)
        self.slot.height, self.progress.height = m.h(28), m.h(24)
        self.reference_label.height = m.h(self.reference_height_px)
        self._root_layout._layout_trigger()

    def on_pre_enter(self, *args):
        palette = _app().mastermorphix_palette
        if self._cube is None or self._cube.palette != palette or self._cube.n != getattr(_app(), "n", 3):
            self._blank(palette)
        self.reset_interaction()
        self._refresh()

    def go_back(self):
        self.manager.current = 'HomeScreen'

    def on_enter(self, *args):
        self.view.cancel_touch()

    def on_pre_leave(self, *args):
        self.reset_interaction()

    def reset_interaction(self):
        self.view.cancel_touch()
        self._cancel_view_turn()

    def _blank(self, palette):
        order = getattr(_app(), "n", 3)
        if self._cube is None or self._cube.n != order:
            self._ori = CubeOrientation(order)
            self.view.camera.azimuth = 0.0
            self.view.camera.elevation = 0.0
        self._cube = MastermorphixCube.solved(palette, order)
        # Fixed center color pairs provide landmarks from the start. Their
        # preset orientations remain editable to match the physical puzzle.
        self._recorded = self.center_preset(set())
        self._history.clear()
        self._preview = None
        if order == 3:
            self._group, self._pos = "center", FACE_NORMALS[self._ori.current_face()]
        else:
            self._pos = min(self._cube.positions, key=lambda p: (sum(abs(v) != max(abs(x) for x in p) for v in p), p))
            self._group = position_kind(self._pos)

    def _all_positions(self):
        return self._cube.positions if self._cube is not None else POSITIONS

    def _positions(self):
        if self._group == "center" and self._cube.n == 3:
            return [FACE_NORMALS[f] for f in AXIS_FACES]
        return sorted((p for p in self._all_positions() if position_kind(p) == self._group), key=position_name)

    def select_position(self, pos):
        if not self.entry_can_edit():
            return
        # Picking the model chooses its input category without a separate tab.
        if pos != self._pos:
            self._gallery_page = 0
        self._pos, self._group = pos, position_kind(pos)
        self._preview = None
        self._refresh()

    def turn_view(self, direction):
        """Use the same animated observation sequence as ordinary advanced input."""
        if not self.entry_can_edit():
            return
        self.view.cancel_touch()
        self._busy_turn = True
        self._pending_dir = direction
        self._controls.disabled = True
        angle, axis = self._ori.prev_axis_deg() if direction < 0 else self._ori.next_axis_deg()
        self.view.animate_whole_turn(axis, angle, .55, on_done=self._after_view_turn)

    def _after_view_turn(self):
        direction = self._pending_dir
        if direction is None:
            return
        if direction < 0:
            self._ori.turn_prev()
        else:
            self._ori.turn_next()
        self._pending_dir = None
        self._busy_turn = False
        self._controls.disabled = False
        self.view.set_whole_world(self._ori.world)

    def _cancel_view_turn(self):
        interrupted = self._busy_turn or self.view._whole_anim is not None
        self.view._cancel_whole_anim()
        self._pending_dir = None
        self._busy_turn = False
        self._controls.disabled = False
        if interrupted:
            self.view.set_whole_world(self._ori.world)

    def _refresh(self):
        if self._cube is None:
            return
        # set_cube cancels animation; clear the matching screen lock as well.
        self._cancel_view_turn()
        self._resize()
        self.title.text = f"{tr('directory.order', order=self._cube.n)} · {tr('morphix.title')}"
        self.demo_button.opacity = 1
        self.demo_button.disabled = False
        def pair(pos):
            return "/".join(str(self._cube.palette.index(c)+1) for c in piece_colors(pos, self._cube.palette, self._cube.n))
        if self._cube.n == 2:
            self.reference_label.text = ""
        else:
            def face_anchor(face):
                candidates = [p for p in self._all_positions() if position_name(p) == face and position_kind(p) == "center"]
                return min(candidates, key=lambda p: sum(v*v for v in p)) if candidates else FACE_NORMALS[face]
            self.reference_label.text = tr("morphix.reference", front=pair(face_anchor("F")), up=pair(face_anchor("U")))
        self.view.recorded = self._recorded
        self.view.selected_pos = self._pos
        # Keep observation orientation through selection, edits and re-entry.
        self.view.set_cube(self._cube)
        self.view.set_whole_world(self._ori.world)
        positions = self._positions()
        kind = tr(f"morphix.group.{self._group}")
        self.slot.text = tr("morphix.slot", kind=kind, i=positions.index(self._pos)+1,
                            total=len(positions), pos=position_name(self._pos))
        self._refresh_palette_button()
        self._build_gallery()
        self.progress.text = tr("morphix.progress", done=len(self._recorded), total=len(self._all_positions()))
        piece = self._cube.cubies[self._pos]
        small_triangle = self._group == "corner" and len(piece_colors(piece.home, self._cube.palette, self._cube.n)) == 1
        self.rotate.disabled = self._pos not in self._recorded or small_triangle
        hint = "hint" if self._pos not in self._recorded else "triangle_hint" if small_triangle else "rotate_hint"
        if self._group == "center" and self._pos in self._recorded:
            hint = "center_hint"
        self.hint.text = tr(f"morphix.{hint}")

    def _build_gallery(self):
        token=self.entry_gallery_generation()
        self.gallery.clear_widgets()
        if self._group == "center" and self._cube.n == 3:
            homes = [self._pos]
        else:
            # High-order centers/wings belong to several distinct orbits.
            # A card must actually fit this slot; other orbit coordinates
            # have no proper orientation and used to crash the gallery.
            homes = [p for p in self._all_positions() if position_kind(p) == self._group
                     and placements(p, self._pos)]
            if self._group == "corner":
                # Four single-color triangles above the four three-color tips.
                homes.sort(key=lambda home: len(piece_colors(home, self._cube.palette, self._cube.n)))
            elif self._cube.n > 3:
                homes.sort(key=lambda home: (piece_colors(home, self._cube.palette, self._cube.n), home))
            elif self._group == "edge":
                # Same-color wedges are indistinguishable; the solver assigns
                # their three internal identities without asking the user.
                homes = [next(p for p in homes if piece_colors(p, self._cube.palette, self._cube.n) == (color,))
                         for color in self._cube.palette]
        choices = ([(home, frame) for home in homes for frame in placements(home, self._pos)]
                   if self._group == "center" and self._cube.n == 3 else [(home, None) for home in homes])
        page_size = GALLERY_PAGE_SIZE
        page_count = max(1, (len(choices) + page_size - 1) // page_size)
        self._gallery_page = max(0, min(self._gallery_page, page_count - 1))
        start = self._gallery_page * page_size
        visible_choices = choices[start:start + page_size]
        self.gallery_pages.set_page(self._gallery_page, page_count)
        for home, chosen_frame in visible_choices:
            frame = placements(home, self._pos)[0]
            current = self._cube.cubies[self._pos]
            active = self._pos in self._recorded and (current.home == home or
                      (self._cube.n <= 3 and self._group == "edge" and piece_colors(current.home, self._cube.palette, self._cube.n) == piece_colors(home, self._cube.palette, self._cube.n)))
            if active:
                if current.home == home:
                    frame = current.frame
                else:
                    frame = next(c.frame for c in equivalent_placements(current, self._cube.palette, self._cube.n) if c.home == home)
            if chosen_frame is not None:
                frame = chosen_frame
                active = active and current.frame == frame
            button = UIButton(text="", active=active)
            preview = MastermorphixView(size_hint=(.9, .9), pos_hint={"center_x": .5, "center_y": .5})
            preview.lock_rotation = True
            preview.fit_piece = True
            preview.set_cube(MastermorphixCube({self._pos: make_piece(home, self._pos, frame, self._cube.n)}, self._cube.palette, self._cube.n))
            _thumbnail_camera_for(preview, self._pos)
            button.add_widget(preview)
            button.bind(pos=lambda b, *_: setattr(b.children[0], "pos", (b.x+b.width*.05, b.y+b.height*.05)),
                        size=lambda b, *_: setattr(b.children[0], "size", (b.width*.9, b.height*.9)))
            button.bind(on_release=lambda _, h=home, f=frame, t=token:
                        self.entry_gallery_action(t,self.choose_piece,h,f))
            self.gallery.add_widget(button)
        rows = max(1, (len(self.gallery.children) + self.gallery.cols - 1) // self.gallery.cols)
        self.gallery.height = rows*m.h(66) + (rows-1)*m.h(6)

    def _change_gallery_page(self, delta):
        if not self.entry_can_edit():return
        self._gallery_page += delta
        self._refresh()

    def _remember(self):
        self._history.append((self._cube.clone(), set(self._recorded)))
        self._history = self._history[-40:]
        _app().solve_result = None

    def choose_piece(self, home, frame=None):
        if not self.entry_can_edit():return
        self._remember()
        frame = frame or placements(home, self._pos)[0]
        self._cube.cubies[self._pos] = make_piece(home, self._pos, frame, self._cube.n)
        self._recorded.add(self._pos)
        self._refresh()

    def rotate_piece(self):
        if not self.entry_can_edit() or self.rotate.disabled:
            return
        self._remember()
        piece = self._cube.cubies[self._pos]
        frames = placements(piece.home, self._pos)
        frame = frames[(frames.index(piece.frame)+1) % len(frames)]
        self._cube.cubies[self._pos] = make_piece(piece.home, self._pos, frame, self._cube.n)
        self._refresh()

    def undo(self):
        if not self.entry_can_edit():
            return
        if self._history:
            self._cube, self._recorded = self._history.pop()
            _app().solve_result=None
            self._refresh()

    def _popup(self, title, content, size=(.9, .8)):
        popup = Popup(title=title, content=content, size_hint=size)
        theme_popup(popup, _app().theme)
        popup.open()
        return popup

    def confirm_clear(self):
        if not self.entry_can_edit():
            return
        content = ResponsiveBoxLayout(orientation="vertical", gap_px=12, padding_px=16)
        content.add_widget(Label(text=tr("morphix.clear_confirm")))
        row = ResponsiveBoxLayout(height_px=48, gap_px=8)
        cancel, ok = UIButton(icon_name="cancel"), DangerButton(icon_name="clear")
        row.add_widget(cancel)
        row.add_widget(ok)
        content.add_widget(row)
        popup = self._popup(tr("confirm.title"), content, (.86, .32))
        cancel.bind(on_release=lambda *_: popup.dismiss())
        ok.bind(on_release=lambda *_: (self._clear_entries(), popup.dismiss()))

    def _clear_entries(self):
        if not self.entry_can_edit() or self._cube is None:
            return
        self._remember()
        history=list(self._history)
        self._blank(self._cube.palette)
        self._history=history
        self._refresh()

    def open_demo(self):
        from demo.coverage import supports,open_tutorial
        if self._cube is not None and supports(self._cube.puzzle_kind,self._cube.n):
            return open_tutorial(self)
        from candidate_puzzles import BY_KIND
        if self._cube is not None and self._cube.puzzle_kind in BY_KIND:
            from demo.expanded_support import open_tutorial
            return open_tutorial(self)
        if self._busy_turn or self._cube is None or self._cube.n > 5:
            return
        self.manager.get_screen("DemoMenuScreen").set_mode((self._cube.puzzle_kind, self._cube.n))
        self.manager.current = "DemoMenuScreen"

    # ---- EntryActionsMixin 钩子 ----
    entry_twist_screen = "MorphixTwistScreen"

    def entry_can_twist(self):
        return not self._busy_turn and self._cube is not None

    def entry_prepare_twist(self):
        self.reset_interaction()
        _app().morphix_twist_source = self.name

    def open_help(self):
        content = ResponsiveBoxLayout(orientation="vertical", gap_px=12, padding_px=16)
        reference = MastermorphixView(size_hint_y=None, height=m.h(180))
        reference.show_axes = True
        reference.set_cube(MastermorphixCube.solved(self._cube.palette, self._cube.n))
        content.add_widget(reference)
        scroll = ScrollView()
        text = Label(text=tr("morphix.help"), size_hint_y=None, halign="left", valign="top", font_size="15sp")
        text.bind(width=lambda label, width: setattr(label, "text_size", (width, None)),
                  texture_size=lambda label, size: setattr(label, "height", size[1]))
        scroll.add_widget(text)
        content.add_widget(scroll)
        demo = UIButton(text=tr("morphix.demo"))
        demo.size_hint_y, demo.height = None, m.h(48)
        content.add_widget(demo)
        popup = self._popup(tr("morphix.title"), content)
        demo.bind(on_release=lambda *_: (popup.dismiss(), self.open_demo()))

    def load_sample(self):
        self.random_load()

    def random_load(self):
        """Fill a complete, legal scramble using the advanced-input generator."""
        if not self.entry_can_edit() or self._cube is None:
            return
        from cube.scramble import random_scramble
        moves = random_scramble(self._cube.n, puzzle_kind="mastermorphix")
        work=MastermorphixCube.solved(self._cube.palette,self._cube.n)
        work.apply_moves(moves)
        self._remember()
        self._cube=work
        self._recorded = set(self._all_positions())
        self._refresh()
        self.hint.text = tr("morphix.random_loaded", k=len(moves), total=len(self._all_positions()))

    def _refresh_palette_button(self):
        visible=self.supports_palette_settings and self._cube is not None and self._cube.puzzle_kind!='football'
        if visible and self.palette_button.parent is None:
            self.navigation.add_widget(self.palette_button,index=2)
        elif not visible and self.palette_button.parent is self.navigation:
            self.navigation.remove_widget(self.palette_button)
        self.palette_button.disabled=not visible

    def palette_colors(self):
        return [COLOR_INFO[c][1] for c in self._cube.palette]

    def default_palette_colors(self):
        return [COLOR_INFO[c][1] for c in DEFAULT_PALETTE]

    def apply_palette_colors(self,colors):
        self._apply_colors([list(c) for c in colors])

    def open_palette_settings(self,index=0):
        if not self.entry_can_edit() or self._cube is None or not self.supports_palette_settings:
            return
        if self._cube.puzzle_kind=='football':
            return
        screen=self.manager.get_screen('PiecePaletteScreen')
        screen.configure(self,index)
        self.manager.current='PiecePaletteScreen'

    def edit_color(self,index):
        self.open_palette_settings(index)

    def restore_preset(self):
        if self._cube is not None and not self._busy_turn:
            self._apply_colors(DEFAULT_PALETTE)

    def _apply_colors(self, entries):
        """Share persistence and draft preservation for color edits and reset."""
        palette = save_palette(entries)
        app = _app()
        app.mastermorphix_palette = palette
        app.solve_result = None
        self._cube.palette = palette
        for previous, _recorded in self._history:
            previous.palette = palette
        if getattr(app.cube, "puzzle_kind", None) == "mastermorphix":
            app.cube.palette = palette
        self._refresh()

    @validation_action
    def check(self):
        if len(self._recorded) != len(self._all_positions()):
            self.hint.text = tr("morphix.error.incomplete", total=len(self._all_positions()))
            return None
        if self._cube.n == 3:
            try:
                cube = normalize_input(self._cube)
            except MorphixInputError as exc:
                self.hint.text = tr(f"morphix.error.{exc}")
                return None
        else:
            cube = self._cube.clone()
        self.hint.text = tr("morphix.valid")
        return cube

    def entry_can_assign(self):
        return self._cube is not None and not getattr(self, "_busy_turn", False)

    def entry_reset_solved(self):
        self._remember()
        history=list(self._history)
        self._blank(getattr(self._cube, "palette", None))
        self._history=history
        # 还原态即全部块都已录入并归位，否则视图会显示成「未录入」。
        self._recorded = set(self._all_positions())

    def entry_commit_state(self):
        app = _app()
        app.cube = self._cube
        app.n = self._cube.n
        app.puzzle_kind = getattr(self._cube, "puzzle_kind", "mastermorphix")
        app.solve_result = None
        self._refresh()

    def entry_set_status(self, text, error=False):
        self.hint.text = text

    def entry_center_preset(self):
        if self._cube is None or self._cube.n != 3:
            return set()
        return {p for p in self._cube.positions if position_kind(p) == "center"}

    def start_solve(self):
        if not self.entry_can_edit():
            return
        cube = self.check()
        if cube is None:
            return
        app = _app()
        app.cube = cube
        app.n = cube.n
        app.puzzle_kind = "mastermorphix"
        app.solve_result = None
        if self.manager.get_screen('SolvingScreen').configure(_app().cube,self.name) is False:return
        self.manager.current = "SolvingScreen"

    def retranslate(self):
        self.follow_control.retranslate()
        self.title.text = tr("morphix.title")
        self._refresh()
