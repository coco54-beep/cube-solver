"""Unified puzzle home with shared order and variant pickers."""
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from app.i18n import tr
from ui.widgets import metrics as m
from ui.widgets.buttons import UIButton, GearButton
from ui.widgets.dialogs import theme_popup
from ui.screens.irregular_directory_screen import (
    PUZZLES, IrregularDirectoryScreen, _app, picker_label,picker_orders)


HOME_GROUPS = {
    'mirror_ghost_group': ('mirror', 'ghost'),
    'drum_pentahedron_group': ('war_drum', 'pentahedron'),
    'shape_mod_group': ('windmill', 'axis', 'fisher'),
}
_GROUP_BY_FAMILY = {family: group for group, families in HOME_GROUPS.items()
                    for family in families}


class HomeScreen(IrregularDirectoryScreen):
    category_groups = HOME_GROUPS
    puzzle_keys = tuple(dict.fromkeys(_GROUP_BY_FAMILY.get(key, key)
                                      for key in ('cube',) + PUZZLES))
    title_key = 'app.name'
    hint_key = 'directory.home_hint'
    menu_top_px = 44
    menu_bottom_px = 44

    def _build_topbar(self, top):
        top.height = m.h(44)
        top.add_widget(BoxLayout())
        self.settings_top_btn = GearButton(size_hint=(None, 1), width=m.h(44))
        self.settings_top_btn.bind(on_release=lambda *_: self.open_settings())
        top.add_widget(self.settings_top_btn)

    def _build_bottom(self):
        bottom = BoxLayout(size_hint_y=None, height=m.h(44), spacing=m.h(8))
        self.formula_btn = UIButton(icon_name='sigma', size_hint=(None, None),
                                   width=m.h(44), height=m.h(44))
        self.formula_btn.bind(on_release=lambda *_: self.open_formula_help())
        self.camera_btn = UIButton(icon_name='camera', size_hint=(None, None),
                                  width=m.h(44), height=m.h(44))
        self.camera_btn.bind(on_release=lambda *_: self.open_camera())
        self.search_btn = UIButton(icon_name='search', size_hint=(None, None),
                                  width=m.h(44), height=m.h(44))
        self.search_btn.bind(on_release=lambda *_: self.open_search())
        self._toolbar_buttons = (self.formula_btn, self.camera_btn, self.search_btn)
        left = BoxLayout(spacing=m.h(8))
        left.add_widget(self.formula_btn)
        left.add_widget(BoxLayout())
        right = BoxLayout()
        right.add_widget(BoxLayout())
        right.add_widget(self.search_btn)
        bottom.add_widget(left)
        bottom.add_widget(self.camera_btn)
        bottom.add_widget(right)
        return bottom

    def on_pre_enter(self, *_args):
        # Returning from playback can leave the directory scrolled outside
        # the grid while the cached window size prevents a relayout.
        if hasattr(self, 'scroll'):
            self.scroll.scroll_y = 1
        self._last_window_size = None
        Clock.schedule_once(lambda *_: self._relayout(), 0)

    def _relayout(self, *_args):
        super()._relayout(*_args)
        self._topbar.height = m.h(44)
        self.settings_top_btn.width = self.settings_top_btn.height = self._topbar.height
        for button in self._toolbar_buttons:
            button.width = button.height = self._bottom.height
        self._bottom.height = self.formula_btn.height

    def refresh_theme(self):
        super().refresh_theme()
        self.settings_top_btn.refresh_theme()
        for button in self._toolbar_buttons:
            button.refresh_theme()


    def _search_entries(self):
        entries = []
        families = []
        for category in self.puzzle_keys:
            if category in HOME_GROUPS:
                entries.append((tr('directory.' + category), category, None))
            families.extend(HOME_GROUPS.get(category, (category,)))
        for puzzle in families:
            title = tr('directory.' + puzzle)
            entries.append((title, puzzle, None))
            orders = picker_orders(puzzle)
            for order in orders:
                try:
                    label, _ = picker_label(puzzle, order)
                except (KeyError, TypeError):
                    continue
                entries.append((title + ' / ' + label, puzzle, order))
        return entries

    def open_search(self):
        if getattr(self, '_search_popup', None) is not None:
            return
        content = BoxLayout(orientation='vertical', spacing=m.h(8), padding=m.h(12))
        edit = TextInput(text='', multiline=False, size_hint_y=None,
                         height=m.h(46), font_size=m.font(16),
                         hint_text=tr('search.hint'))
        content.add_widget(edit)
        results_box = BoxLayout(orientation='vertical', size_hint_y=None,
                                spacing=m.h(4))
        results_box.bind(minimum_height=results_box.setter('height'))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(results_box)
        content.add_widget(scroll)
        back = UIButton(text=tr('directory.back'), size_hint_y=None,
                        height=m.h(40))
        content.add_widget(back)
        popup = Popup(title=tr('search.title'), content=content,
                      size_hint=(.78, .78), auto_dismiss=True)
        theme_popup(popup, _app().theme)
        self._search_popup = popup

        def choose(puzzle, order):
            popup.dismiss()
            if order is None:
                self._open_series(puzzle)
            else:
                self.launch_order(puzzle, order)

        def rebuild(value):
            results_box.clear_widgets()
            query = value.strip().casefold()
            if query:
                matches = [item for item in entries
                           if query in item[0].casefold()]
            else:
                matches = [item for item in entries
                           if item[2] is None and item[1] in self.puzzle_keys]
            for label, puzzle, order in matches[:80]:
                button = UIButton(text=label, size_hint_y=None,
                                  height=m.h(42), halign='left', valign='middle')
                button.bind(width=lambda b, w: setattr(
                    b, 'text_size', (max(0, w - m.h(16)), None)))
                button.bind(on_release=lambda *_args, p=puzzle, o=order:
                            choose(p, o))
                results_box.add_widget(button)
            if not matches:
                empty = Label(text=tr('search.empty'), color=_app().theme.text_muted,
                              size_hint_y=None, height=m.h(44),
                              halign='center', valign='middle')
                empty.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
                results_box.add_widget(empty)

        entries = self._search_entries()
        edit.bind(text=lambda _w, value: rebuild(value))
        back.bind(on_release=lambda *_: popup.dismiss())
        popup.bind(on_dismiss=lambda *_: setattr(self, '_search_popup', None))
        rebuild('')
        popup.open()
        Clock.schedule_once(lambda *_: setattr(edit, 'focus', True), 0)

    def open_settings(self):
        self.manager.current = 'SettingsScreen'

    def open_camera(self):
        app = _app()
        if app is not None:
            app.selection_series = None
        from ui.widgets.photo_entry import choose_photo_puzzle
        choose_photo_puzzle(self)

    def open_formula_help(self):
        self.manager.current = 'FormulaLibraryScreen'
