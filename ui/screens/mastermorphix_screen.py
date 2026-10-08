"""Piece input for a scrambled Mastermorphix, including shape/orientation."""

import math
from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.colorpicker import ColorPicker

from app.constants import COLOR_INFO, COLOR_ORDER
from app.i18n import tr
from app.mastermorphix_palette import palette_entries, save_palette
from cube.mastermorphix import (MastermorphixCube, DEFAULT_PALETTE, POSITIONS, AXIS_FACES, position_kind, position_name,
                               placements, make_piece, piece_colors, equivalent_placements,
                               normalize_input, MorphixInputError)
from cube.coordinates import FACE_NORMALS
from renderer.mastermorphix_view import MastermorphixView
from renderer.cube_orientation import CubeOrientation
from ui.widgets.buttons import UIButton, PrimaryButton, DangerButton
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets import metrics as m
from ui.widgets.dialogs import theme_popup
from ui.widgets.mastermorphix_net import MastermorphixNet


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


class MastermorphixScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cube = None
        self._recorded = set()
        self._history = []
        self._group = "center"
        self._pos = (0, 1, 0)
        self._preview = None
        self._ori = CubeOrientation(3)
        self._busy_turn = False
        self._pending_dir = None
        self.build_ui()

    def build_ui(self):
        root = ResponsiveBoxLayout(orientation="vertical", gap_px=6,
                                   padding_px=[28, 6, 28, 8])
        top = ResponsiveBoxLayout(height_px=44, gap_px=8)
        back = UIButton(icon_name="back", size_hint_x=.16)
        back.bind(on_release=lambda *_: setattr(self.manager, "current", "HomeScreen"))
        self.title = Label(text=tr("morphix.title"), font_size="20sp", bold=True)
        demo_button = UIButton(icon_name="demo", size_hint_x=.16)
        demo_button.bind(on_release=lambda *_: self.open_demo())
        for widget in (back, self.title, demo_button):
            top.add_widget(widget)
        root.add_widget(top)
        self.palette_row = ResponsiveBoxLayout(height_px=34, gap_px=8)
        root.add_widget(self.palette_row)
        self.reference_label = Label(size_hint_y=None, height=m.h(24), font_size="12sp", halign="center")
        root.add_widget(self.reference_label)
        self.view = MastermorphixView()
        # CubeOrientation aligns each observation axis with +Z. Use the same
        # straight-on camera as advanced input, rather than CubeView's tilt.
        self.view.camera.azimuth = 0.0
        self.view.camera.elevation = 0.0
        self.view.lock_rotation = True
        self.view.show_axes = True
        self.view.on_pick_piece = self.select_position
        self.main = ResponsiveBoxLayout(orientation="vertical", gap_px=8)
        self.main.add_widget(self.view)
        root.add_widget(self.main)
        controls = ResponsiveBoxLayout(orientation="vertical", gap_px=6, size_hint_y=None)
        controls.bind(minimum_height=controls.setter("height"))
        self._controls = controls
        self._controls_scroll = ScrollView(do_scroll_x=False, bar_width=m.h(3))
        self._controls_scroll.add_widget(controls)
        self.main.add_widget(self._controls_scroll)
        self.slot = Label(size_hint_y=None, height=m.h(28), font_size="14sp")
        controls.add_widget(self.slot)
        self.gallery = GridLayout(cols=4, size_hint_y=None, height=m.h(66), spacing=m.h(6))
        controls.add_widget(self.gallery)
        navigation = ResponsiveBoxLayout(height_px=46, gap_px=8)
        self.btn_prev = UIButton(icon_name="prev")
        self.btn_prev.bind(on_release=lambda *_: self.turn_view(-1))
        self.rotate = UIButton(icon_name="reset")
        self.rotate.bind(on_release=lambda *_: self.rotate_piece())
        self.btn_next = UIButton(icon_name="next")
        self.btn_next.bind(on_release=lambda *_: self.turn_view(1))
        for button in (self.btn_prev, self.rotate, self.btn_next):
            navigation.add_widget(button)
        controls.add_widget(navigation)
        self.hint = Label(text=tr("morphix.hint"), size_hint_y=None, height=m.h(44),
                          font_size="12sp", halign="center", valign="middle")
        self.hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        controls.add_widget(self.hint)
        actions = ResponsiveBoxLayout(height_px=48, gap_px=8)
        for icon, cls, callback in (("random", UIButton, self.random_load),
                                    ("clear", DangerButton, self.confirm_clear),
                                    ("undo", UIButton, self.undo),
                                    ("check", UIButton, self.check),
                                    ("solve", PrimaryButton, self.start_solve)):
            button = cls(icon_name=icon)
            button.bind(on_release=lambda _, cb=callback: cb())
            actions.add_widget(button)
        controls.add_widget(actions)
        self.progress = Label(size_hint_y=None, height=m.h(24), font_size="13sp")
        controls.add_widget(self.progress)
        self.add_widget(root)
        self.bind(size=lambda *_: self._resize())
        controls.bind(minimum_height=lambda *_: self._resize())

    def _resize(self):
        rows = 2 if self._group == "corner" else 1
        self.gallery.height = rows*m.h(66) + (rows-1)*m.h(6)
        self.gallery.spacing = m.h(6)
        self.slot.height, self.hint.height, self.progress.height = m.h(28), m.h(44), m.h(24)
        self.reference_label.height = m.h(24)
        wide = self.width > self.height * 1.15
        self.main.orientation = "horizontal" if wide else "vertical"
        self.view.size_hint = (.48, 1) if wide else (1, 1)
        self._controls_scroll.size_hint = (.52, 1) if wide else (1, None)
        if not wide:
            self._controls_scroll.height = min(self._controls.minimum_height, self.height*.56)

    def on_pre_enter(self, *args):
        palette = _app().mastermorphix_palette
        if self._cube is None or self._cube.palette != palette:
            self._blank(palette)
        self.reset_interaction()
        self._refresh()

    def on_enter(self, *args):
        self.view.cancel_touch()

    def on_pre_leave(self, *args):
        self.reset_interaction()

    def reset_interaction(self):
        self.view.cancel_touch()
        self._cancel_view_turn()

    def _blank(self, palette):
        self._cube = MastermorphixCube.solved(palette)
        # Fixed center color pairs provide landmarks from the start. Their
        # preset orientations remain editable to match the physical puzzle.
        self._recorded = {p for p in POSITIONS if position_kind(p) == "center"}
        self._history.clear()
        self._preview = None
        self._group, self._pos = "center", FACE_NORMALS[self._ori.current_face()]

    def _positions(self):
        if self._group == "center":
            return [FACE_NORMALS[f] for f in AXIS_FACES]
        return sorted((p for p in POSITIONS if position_kind(p) == self._group), key=position_name)

    def select_position(self, pos):
        if self._busy_turn:
            return
        # Picking the model chooses its input category without a separate tab.
        self._pos, self._group = pos, position_kind(pos)
        self._preview = None
        self._refresh()

    def turn_view(self, direction):
        """Use the same animated observation sequence as ordinary advanced input."""
        if self._busy_turn:
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
        def pair(pos):
            return "/".join(str(self._cube.palette.index(c)+1) for c in piece_colors(pos, self._cube.palette))
        self.reference_label.text = tr("morphix.reference", front=pair((0, 0, 1)), up=pair((0, 1, 0)))
        self.view.recorded = self._recorded
        self.view.selected_pos = self._pos
        # Keep observation orientation through selection, edits and re-entry.
        self.view.set_cube(self._cube)
        self.view.set_whole_world(self._ori.world)
        positions = self._positions()
        kind = tr(f"morphix.group.{self._group}")
        self.slot.text = tr("morphix.slot", kind=kind, i=positions.index(self._pos)+1,
                            total=len(positions), pos=position_name(self._pos))
        self.palette_row.clear_widgets()
        for index, color in enumerate(self._cube.palette):
            chip = _Swatch(COLOR_INFO[color][1], text=str(index+1))
            chip.bind(on_release=lambda _, i=index: self.edit_color(i))
            self.palette_row.add_widget(chip)
        self._build_gallery()
        self.progress.text = tr("morphix.progress", done=len(self._recorded))
        piece = self._cube.cubies[self._pos]
        small_triangle = self._group == "corner" and len(piece_colors(piece.home, self._cube.palette)) == 1
        self.rotate.disabled = self._pos not in self._recorded or small_triangle
        hint = "hint" if self._pos not in self._recorded else "triangle_hint" if small_triangle else "rotate_hint"
        if self._group == "center" and self._pos in self._recorded:
            hint = "center_hint"
        self.hint.text = tr(f"morphix.{hint}")

    def _build_gallery(self):
        self.gallery.clear_widgets()
        if self._group == "center":
            homes = [self._pos]
        else:
            homes = [p for p in POSITIONS if position_kind(p) == self._group]
            if self._group == "corner":
                # Four single-color triangles above the four three-color tips.
                homes.sort(key=lambda home: len(piece_colors(home, self._cube.palette)))
            elif self._group == "edge":
                # Same-color wedges are indistinguishable; the solver assigns
                # their three internal identities without asking the user.
                homes = [next(p for p in homes if piece_colors(p, self._cube.palette) == (color,))
                         for color in self._cube.palette]
        choices = [(home, frame) for home in homes for frame in placements(home, self._pos)] if self._group == "center" else [(home, None) for home in homes]
        for home, chosen_frame in choices:
            frame = placements(home, self._pos)[0]
            current = self._cube.cubies[self._pos]
            active = self._pos in self._recorded and (current.home == home or
                      (self._group == "edge" and piece_colors(current.home, self._cube.palette) == piece_colors(home, self._cube.palette)))
            if active:
                if current.home == home:
                    frame = current.frame
                else:
                    frame = next(c.frame for c in equivalent_placements(current, self._cube.palette) if c.home == home)
            if chosen_frame is not None:
                frame = chosen_frame
                active = active and current.frame == frame
            button = UIButton(text="", active=active)
            preview = MastermorphixView(size_hint=(.9, .9), pos_hint={"center_x": .5, "center_y": .5})
            preview.lock_rotation = True
            preview.fit_piece = True
            preview.set_cube(MastermorphixCube({self._pos: make_piece(home, self._pos, frame)}, self._cube.palette))
            _thumbnail_camera_for(preview, self._pos)
            button.add_widget(preview)
            button.bind(pos=lambda b, *_: setattr(b.children[0], "pos", (b.x+b.width*.05, b.y+b.height*.05)),
                        size=lambda b, *_: setattr(b.children[0], "size", (b.width*.9, b.height*.9)))
            button.bind(on_release=lambda _, h=home, f=frame: self.choose_piece(h, f))
            self.gallery.add_widget(button)

    def _remember(self):
        self._history.append((self._cube.clone(), set(self._recorded)))
        self._history = self._history[-40:]
        _app().solve_result = None

    def choose_piece(self, home, frame=None):
        self._remember()
        frame = frame or placements(home, self._pos)[0]
        self._cube.cubies[self._pos] = make_piece(home, self._pos, frame)
        self._recorded.add(self._pos)
        self._refresh()

    def rotate_piece(self):
        if self.rotate.disabled:
            return
        self._remember()
        piece = self._cube.cubies[self._pos]
        frames = placements(piece.home, self._pos)
        frame = frames[(frames.index(piece.frame)+1) % len(frames)]
        self._cube.cubies[self._pos] = make_piece(piece.home, self._pos, frame)
        self._refresh()

    def undo(self):
        if self._history:
            self._cube, self._recorded = self._history.pop()
            self._refresh()

    def _popup(self, title, content, size=(.9, .8)):
        popup = Popup(title=title, content=content, size_hint=size)
        theme_popup(popup, _app().theme)
        popup.open()
        return popup

    def confirm_clear(self):
        content = ResponsiveBoxLayout(orientation="vertical", gap_px=12, padding_px=16)
        content.add_widget(Label(text=tr("morphix.clear_confirm")))
        row = ResponsiveBoxLayout(height_px=48, gap_px=8)
        cancel, ok = UIButton(icon_name="cancel"), DangerButton(icon_name="clear")
        row.add_widget(cancel)
        row.add_widget(ok)
        content.add_widget(row)
        popup = self._popup(tr("confirm.title"), content, (.86, .32))
        cancel.bind(on_release=lambda *_: popup.dismiss())
        ok.bind(on_release=lambda *_: (self._blank(self._cube.palette), self._refresh(), popup.dismiss()))

    def open_demo(self):
        if self._busy_turn:
            return
        self.manager.get_screen("DemoMenuScreen").set_mode("mastermorphix")
        self.manager.current = "DemoMenuScreen"

    def open_help(self):
        content = ResponsiveBoxLayout(orientation="vertical", gap_px=12, padding_px=16)
        reference = MastermorphixView(size_hint_y=None, height=m.h(180))
        reference.show_axes = True
        reference.set_cube(MastermorphixCube.solved(self._cube.palette))
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
        if self._busy_turn or self._cube is None:
            return
        from cube.scramble import random_scramble
        moves = random_scramble(3)
        self._remember()
        self._cube = MastermorphixCube.solved(self._cube.palette)
        self._cube.apply_moves(moves)
        self._recorded = set(POSITIONS)
        self._refresh()
        self.hint.text = tr("morphix.random_loaded", k=len(moves))

    def edit_color(self, index):
        """Edit one top swatch directly, keeping the entered pieces and pose."""
        if self._cube is None or self._busy_turn:
            return
        content = ResponsiveBoxLayout(orientation="vertical", gap_px=8, padding_px=16)
        hint = Label(text=tr("morphix.color_hint"), size_hint_y=None, height=m.h(36),
                     font_size="12sp", halign="center")
        hint.bind(size=lambda label, *_: setattr(label, "text_size", label.size))
        content.add_widget(hint)
        reference = MastermorphixNet(colors=[COLOR_INFO[c][1] for c in self._cube.palette],
                                    selected_face=index, size_hint_y=None, height=m.h(140))
        content.add_widget(reference)
        picker = ColorPicker(color=COLOR_INFO[self._cube.palette[index]][1])
        content.add_widget(picker)

        def preview_color(_picker, color):
            colors = [COLOR_INFO[c][1] for c in self._cube.palette]
            rgb = tuple(color[:3])
            for other, rgba in enumerate(colors):
                if other != index and rgba[:3] == rgb:
                    colors[other] = colors[index]
                    break
            colors[index] = rgb + (1.,)
            reference.colors = colors
        picker.bind(color=preview_color)
        actions = ResponsiveBoxLayout(height_px=48, gap_px=8)
        cancel, done = UIButton(icon_name="cancel"), PrimaryButton(icon_name="done")
        restore = UIButton(text=tr("morphix.restore_preset"), size_hint_x=2,
                           font_size="14sp", halign="center", valign="middle")
        restore.bind(size=lambda button, *_: setattr(button, "text_size", button.size))
        actions.add_widget(cancel)
        actions.add_widget(restore)
        actions.add_widget(done)
        content.add_widget(actions)
        popup = self._popup(tr("morphix.color_slot", i=index+1), content, (.92, .85))
        cancel.bind(on_release=lambda *_: popup.dismiss())
        restore.bind(on_release=lambda *_: (self.restore_preset(), popup.dismiss()))

        def accept(*_):
            rgb = tuple(picker.color[:3])
            entries = palette_entries(self._cube.palette)
            # Selecting an existing color exchanges slots, preserving four
            # distinct colors and allowing reference pairs to be rearranged.
            for other, color in enumerate(self._cube.palette):
                if other != index and COLOR_INFO[color][1][:3] == rgb:
                    entries[other] = entries[index]
                    break
            entries[index] = next((c for c in COLOR_ORDER if COLOR_INFO[c][1][:3] == rgb),
                                  list(rgb) + [1.])
            self._apply_colors(entries)
            popup.dismiss()
        done.bind(on_release=accept)

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

    def check(self):
        if len(self._recorded) != 26:
            self.hint.text = tr("morphix.error.incomplete")
            return None
        try:
            cube = normalize_input(self._cube)
        except MorphixInputError as exc:
            self.hint.text = tr(f"morphix.error.{exc}")
            return None
        self.hint.text = tr("morphix.valid")
        return cube

    def start_solve(self):
        cube = self.check()
        if cube is None:
            return
        app = _app()
        app.cube = cube
        app.n = 3
        app.puzzle_kind = "mastermorphix"
        app.solve_result = None
        self.manager.current = "SolvingScreen"

    def retranslate(self):
        self.title.text = tr("morphix.title")
        self._refresh()
