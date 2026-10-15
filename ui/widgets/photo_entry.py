"""Shared photo entry points, restricted to supported puzzles up to order five."""
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from app.i18n import tr
from ui.widgets import metrics as m
from ui.widgets.buttons import UIButton
from ui.widgets.dialogs import theme_popup
from vision.scan_profiles import SUPPORTED


def supported(kind, n):
    return n in ((2, 3, 4, 5) if kind == 'cube' else SUPPORTED.get(kind, ()))


def open_existing(screen, cube):
    app = App.get_running_app()
    kind = getattr(cube, 'puzzle_kind', 'cube')
    if not supported(kind, cube.n):
        return
    app.cube, app.n, app.puzzle_kind = cube, cube.n, kind
    app.camera_return_screen = screen.name
    app.input_from_camera = False
    app.camera_shape_result = None
    app.camera_recorded = set(getattr(screen, '_recorded', ())) if kind == 'pandora' else None
    screen.manager.current = 'CameraScreen'


def _choose(title, entries, callback):
    app = App.get_running_app()
    content = BoxLayout(orientation='vertical', spacing=m.h(8), padding=m.h(8))
    hint = Label(text=tr('camera.limit'), size_hint_y=None, height=m.h(32),
                 color=app.theme.text_muted, font_size='13sp')
    content.add_widget(hint)
    scroll = ScrollView(do_scroll_x=False)
    grid = GridLayout(cols=2, spacing=m.h(8), size_hint_y=None)
    grid.bind(minimum_height=grid.setter('height'))
    scroll.add_widget(grid)
    content.add_widget(scroll)
    popup = Popup(title=title, content=content, size_hint=(.93, .8))
    theme_popup(popup, app.theme)
    def selected(value):
        popup.dismiss()
        callback(value)
    for label, value in entries:
        button = UIButton(text=label, size_hint_y=None, height=m.h(56), font_size='14sp')
        button.bind(size=lambda b, *_: setattr(b, 'text_size', (b.width-m.h(8), None)))
        button.bind(on_release=lambda _, v=value: selected(v))
        grid.add_widget(button)
    popup.open()


def choose_photo_puzzle(screen):
    def choose_kind(kind):
        orders = (2, 3, 4, 5) if kind == 'cube' else SUPPORTED[kind]
        def begin(n):
            app = App.get_running_app()
            if kind == 'cube':
                app.new_cube(n)
            elif kind == 'pandora':
                app.new_shape_cube(kind, n)
            else:
                app.new_polyhedral(kind, n)
            open_existing(screen, app.cube)
        if len(orders) == 1:
            begin(orders[0])
        else:
            entries = []
            for n in orders:
                label = tr('directory.order', order=n)
                if kind == 'dino':
                    label += ' · '+tr('directory.dinosaur' if n == 2 else 'directory.lattice')
                entries.append((label, n))
            _choose(tr('camera.choose_order'), entries, begin)
    entries = [(tr('camera.ordinary'), 'cube')]
    for kind in SUPPORTED:
        label = (tr('directory.dinosaur')+' / '+tr('directory.lattice') if kind == 'dino'
                 else tr('directory.'+kind))
        entries.append((label, kind))
    _choose(tr('camera.choose_puzzle'), entries, choose_kind)
