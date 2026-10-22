"""Traditional 3D input layout for both Tangram variants."""
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from app.i18n import tr
from cube.articulated_observation import FACES, color_templates, polygon_key
from cube.polyhedral import CUBE
from renderer.cube_orientation import CubeOrientation
from renderer.tangram_entry_view import TangramEntryView
from ui.widgets import metrics as m
from ui.widgets.buttons import UIButton, PrimaryButton, DangerButton
from ui.widgets.dialogs import theme_popup
from ui.widgets.layouts import AdaptiveSceneLayout, ResponsiveBoxLayout
from ui.widgets.camera_follow import follow_panel


class TangramColorLayout:
    """Reuse the observation draft in the traditional 3D input workflow.

    Ordinary Tangram paints colours; Extreme uses coloured shape cards and a
    direction control, sharing the same main model and face-turn animation.
    """
    def __init__(self, screen):
        self.screen = screen
        self.root = AdaptiveSceneLayout()
        self.original_root = screen._root_layout
        shared = (screen.title, screen.colors, screen.status)
        self.original_slots = tuple((w, w.parent, w.parent.children.index(w)) for w in shared)
        self.original_view = screen.view
        self.view = TangramEntryView()
        self.view.on_paint = self.paint
        self._turn_token = None
        screen._busy_turn = False
        self.active = False
        top = ResponsiveBoxLayout(height_px=44, gap_px=6)
        back = self.button(top, 'back', screen.back)
        back.size_hint_x = .22
        self.top = top
        help_button = self.button(top, 'demo', self.help)
        help_button.size_hint_x = .22
        self.root.add_widget(top)

        self.panel = ResponsiveBoxLayout(orientation='vertical', gap_px=6)
        from ui.screens.tangram_shape_cards import TangramShapeCards
        self.shapes = TangramShapeCards(self)
        self.view.on_shape_point = self.shapes.query_point
        self.face_info = Label(size_hint_y=None, height=m.h(48), font_size='12sp',
                               halign='center', valign='middle')
        self.face_info.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        nav = ResponsiveBoxLayout(height_px=44, gap_px=5)
        self.button(nav, 'prev', lambda: self.change_face(-1))
        self.button(nav, 'gear', screen.customize)
        self.rotate_button = self.button(nav, 'reset', self.shapes.rotate)
        self.view_button = UIButton(text='3D', active=True, font_size='14sp')
        self.view_button.bind(on_release=lambda *_: self.toggle_view())
        nav.add_widget(self.view_button)
        self.button(nav, 'next', lambda: self.change_face(1))
        actions = ResponsiveBoxLayout(height_px=48, gap_px=5)
        self.edit_buttons = []
        for icon, callback, cls in (
                ('twist', screen.open_twist, UIButton),
                ('random', screen.randomize, UIButton),
                ('clear', self.confirm_clear, DangerButton),
                ('undo', screen.undo, UIButton),
                ('target', screen.assign_initial, UIButton),
                ('solve', self.solve_or_cancel, PrimaryButton)):
            self.edit_buttons.append(self.button(actions, icon, callback, cls))
        self.undo_button = self.edit_buttons[3]
        self.solve_button = self.edit_buttons[-1]
        self.nav = nav
        self.actions = actions
        self.nav_buttons = tuple(nav.children)
        self.scene = ResponsiveBoxLayout(orientation='vertical')
        self.scene.add_widget(self.view)
        controls, self.follow_control = follow_panel(self.panel, self.view)
        self.root.set_content(self.scene, controls)

    @staticmethod
    def button(row, icon, callback, cls=UIButton):
        button = cls(icon_name=icon)
        button.bind(on_release=lambda *_: callback())
        row.add_widget(button)
        return button

    def show(self, active):
        if active == self.active:
            return
        screen = self.screen
        screen.board.cancel_touch()
        self.cancel_turn()
        palette = tuple(screen.view.palette)
        for widget, _, _ in self.original_slots:
            widget.parent.remove_widget(widget)
        screen.remove_widget(self.original_root if active else self.root)
        self.active = active
        if active:
            # Kivy children are stored in reverse drawing order.
            self.top.add_widget(screen.title, index=1)
            self.panel.add_widget(screen.colors)
            self.panel.add_widget(self.face_info)
            self.panel.add_widget(self.shapes.caption)
            self.panel.add_widget(self.shapes.gallery)
            self.panel.add_widget(self.shapes.pager)
            self.panel.add_widget(self.nav)
            self.panel.add_widget(self.shapes.hint)
            self.panel.add_widget(self.actions)
            self.panel.add_widget(screen.status)
            screen.view = self.view
            metrics = m.input_grid_metrics(1)
            screen.colors.height = metrics['height']
            screen.colors.spacing = metrics['spacing']
            screen.colors.padding = metrics['padding']
            screen.status.height = m.h(40)
            screen._root_layout = self.root
        else:
            for widget in (self.face_info, self.shapes.caption, self.shapes.gallery,
                           self.shapes.pager, self.nav, self.shapes.hint, self.actions):
                self.panel.remove_widget(widget)
            for widget, parent, index in sorted(self.original_slots, key=lambda item: item[2]):
                parent.add_widget(widget, index=index)
            screen.colors.height = m.h(38)
            screen.colors.spacing = m.h(4)
            screen.colors.padding = 0
            screen.colors.opacity = 1
            screen.colors.disabled = False
            screen.status.height = m.h(50)
            screen._root_layout = self.original_root
            screen.view = self.original_view
            screen.view.set_cube(screen._cube)
        screen.view.palette = palette
        screen.add_widget(screen._root_layout)
        screen._root_layout._layout_trigger()

    def refresh(self):
        screen = self.screen
        if not self.active:
            return
        extreme = screen._cube.puzzle_kind == 'tangram_extreme'
        screen.colors.height = 0 if extreme else m.input_grid_metrics(1)['height']
        screen.colors.opacity = 0 if extreme else 1
        screen.colors.disabled = extreme or screen._job is not None or screen._busy_turn
        self.rotate_button.size_hint_x = 1 if extreme else None
        self.rotate_button.width = m.h(48) if extreme else 0
        self.rotate_button.opacity = 1 if extreme else 0
        self.view_button.size_hint_x = 1 if extreme else None
        self.view_button.width = m.h(48) if extreme else 0
        self.view_button.opacity = 1 if extreme else 0
        self.view_button.color = App.get_running_app().theme.button_text
        face = FACES[screen._ao_face]
        orientation = getattr(screen, '_ori', None)
        if not isinstance(orientation, CubeOrientation) or orientation.current_face() != face:
            orientation = CubeOrientation(3)
            while orientation.current_face() != face:
                orientation.turn_next()
            screen._ori = orientation
        self.view.active_face = screen._ao_face
        self.view.set_draft(screen._cube, screen._ao_state, screen.view.palette, screen._applied())
        self.view_button.active = abs(self.view.yaw) + abs(self.view.pitch) > .01
        self.view.selected = None
        if extreme and self.shapes.location is not None and self.shapes.location[0] == screen._ao_face:
            self.view.selected = screen._ao_face * 1024 + self.shapes.location[1]
        if extreme and self.shapes.key is not None and self.shapes.key[0] == screen._ao_face:
            selected = next((i for i, p in enumerate(screen._ao_state['views'][screen._ao_face])
                             if polygon_key(p['outline']) == self.shapes.key[1]), None)
            if selected is not None:self.view.selected = screen._ao_face * 1024 + selected
        if not screen._busy_turn:
            self.view.set_whole_world(orientation.world)
        normals = tuple(orientation.world.transform(*n) for n in CUBE)
        top = max(range(6), key=lambda i: normals[i][1])
        right = max(range(6), key=lambda i: normals[i][0])
        reference = tr('six.face_reference', top=tr('face.' + FACES[top]), right=tr('face.' + FACES[right]))
        self.face_info.text = screen.face_label.text + '\n' + reference
        self.face_info.color = App.get_running_app().theme.text
        self.shapes.refresh()
        if extreme:
            screen.status.text = screen._message or tr('observe.shape_card_progress',
                panels=sum(map(len, screen._ao_state['views'])))
        self.refresh_controls()
        self.follow_control.retranslate()

    def toggle_view(self):
        if not self.screen.entry_can_edit():return
        self.view.cancel_touch()
        front = abs(self.view.yaw) + abs(self.view.pitch) < .01
        self.view.yaw, self.view.pitch, self.view.roll = (32, 22, 0) if front else (0, 0, 0)
        self.view_button.active = front
        self.view.refresh()

    def refresh_controls(self):
        screen = self.screen
        busy = screen._job is not None or screen._busy_turn
        self.view.disabled = busy
        for button in self.edit_buttons[:-1] + list(self.nav_buttons):
            button.disabled = busy
        for swatch in getattr(screen, '_swatches', ()):
            swatch.disabled = busy
        self.undo_button.disabled = busy or not (screen._ao_undo or screen._history)
        self.solve_button.disabled = screen._busy_turn
        self.solve_button.icon_name = 'cancel' if screen._job is not None else 'solve'
        self.shapes.refresh_controls()

    def change_face(self, delta):
        screen = self.screen
        if not self.active or not screen.entry_can_edit():
            return
        orientation = screen._ori
        angle, axis = orientation.prev_axis_deg() if delta < 0 else orientation.next_axis_deg()
        token = object()
        self._turn_token = token
        screen._busy_turn = True
        self.refresh()

        def finish():
            if self._turn_token is not token or not self.active:
                return
            self._turn_token = None
            orientation.turn_prev() if delta < 0 else orientation.turn_next()
            screen._ao_face = FACES.index(orientation.current_face())
            screen._ao_region = 0
            screen._point = None
            screen._clear_options()
            screen._message = ''
            screen._busy_turn = False
            self.view._polygons = []
            self.view.set_whole_world(orientation.world)
            screen._refresh()

        self.view.animate_whole_turn(axis, angle, .55, on_done=finish)

    def cancel_turn(self):
        self._turn_token = None
        self.view.cancel_touch()
        self.view.cancel_observation()
        self.view._polygons = []
        self.screen._busy_turn = False
        orientation = getattr(self.screen, '_ori', None)
        if isinstance(orientation, CubeOrientation):
            self.view.set_whole_world(orientation.world)
        if self.active:
            self.refresh_controls()

    def paint(self, slots):
        screen = self.screen
        if not self.active or not screen.entry_can_edit():
            return
        face = screen._ao_face
        indices = [slot % 1024 for slot in slots if slot // 1024 == face]
        if not indices:
            return
        draft = screen._get_draft()
        templates = color_templates()[face]
        painted = {polygon_key(p['outline']): p['color'] for p in draft.views[face]}
        if all(painted.get(polygon_key(templates[i])) == screen._color for i in indices):
            return
        screen._remember()
        draft.paint_samples(face, indices, screen._color)
        screen._clear_options()
        screen._sync()

    def solve_or_cancel(self):
        if self.screen._job is not None:
            self.screen.cancel_matching()
        else:
            self.screen.solve()

    def help(self):
        extreme = self.screen._cube.puzzle_kind == 'tangram_extreme'
        self.dialog(tr('observe.shape_entry_title' if extreme else 'observe.color_entry_title'),
                    tr('observe.shape_card_hint' if extreme else 'observe.color_hint'))

    def confirm_clear(self):
        if self.screen.entry_can_edit():
            self.dialog(tr('input.clear.title'), tr('input.clear.msg'), self.screen.clear)

    def dialog(self, title, message, confirm=None):
        content = ResponsiveBoxLayout(orientation='vertical', gap_px=10, padding_px=16)
        label = Label(text=message, halign='center', valign='middle',
                      color=App.get_running_app().theme.text)
        label.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        content.add_widget(label)
        row = ResponsiveBoxLayout(height_px=48, gap_px=8)
        popup = Popup(title=title, content=content, size_hint=(.86, .38))
        self.button(row, 'cancel' if confirm else 'check', popup.dismiss)
        if confirm:
            self.button(row, 'clear', lambda: (confirm(), popup.dismiss()), DangerButton)
        content.add_widget(row)
        theme_popup(popup, App.get_running_app().theme).open()
