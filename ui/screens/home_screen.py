"""Unified puzzle home with shared order and variant pickers."""
from kivy.uix.boxlayout import BoxLayout
from ui.widgets import metrics as m
from ui.widgets.buttons import UIButton, GearButton
from ui.screens.irregular_directory_screen import IrregularDirectoryScreen, PUZZLES, _app


class HomeScreen(IrregularDirectoryScreen):
    puzzle_keys = ('cube',) + PUZZLES
    title_key = 'app.name'
    hint_key = 'directory.home_hint'

    def _build_topbar(self, top):
        top.height = 0

    def _build_bottom(self):
        bottom = BoxLayout(size_hint_y=None, height=m.h(44), spacing=m.h(8))
        self.formula_btn = UIButton(icon_name='sigma', size_hint=(None, None),
                                   width=m.h(44), height=m.h(44))
        self.formula_btn.bind(on_release=lambda *_: self.open_formula_help())
        self.camera_btn = UIButton(icon_name='camera', size_hint=(None, None),
                                  width=m.h(44), height=m.h(44))
        self.camera_btn.bind(on_release=lambda *_: self.open_camera())
        self.settings_btn = GearButton(size_hint=(None, None),
                                       width=m.h(44), height=m.h(44))
        self.settings_btn.bind(on_release=lambda *_: self.open_settings())
        self._toolbar_buttons = (self.formula_btn, self.camera_btn, self.settings_btn)
        left = BoxLayout(spacing=m.h(8))
        left.add_widget(self.formula_btn)
        left.add_widget(BoxLayout())
        right = BoxLayout()
        right.add_widget(BoxLayout())
        right.add_widget(self.settings_btn)
        bottom.add_widget(left)
        bottom.add_widget(self.camera_btn)
        bottom.add_widget(right)
        return bottom

    def _relayout(self, *_args):
        super()._relayout(*_args)
        self._topbar.height = 0
        self._bottom.height = self.formula_btn.height

    def refresh_theme(self):
        super().refresh_theme()
        for button in self._toolbar_buttons:
            button.refresh_theme()

    def open_settings(self):
        self.manager.current = 'SettingsScreen'

    def open_camera(self):
        from ui.widgets.photo_entry import choose_photo_puzzle
        choose_photo_puzzle(self)

    def open_formula_help(self):
        self.manager.current = 'FormulaLibraryScreen'
