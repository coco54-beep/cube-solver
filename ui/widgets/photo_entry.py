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


def photo_groups():
    """Filter the current home catalogue; never maintain a second taxonomy."""
    from ui.screens.irregular_directory_screen import PUZZLES,picker_orders
    result=[];seen=set()
    for family in ('cube',)+PUZZLES:
        options=(family,)+tuple(picker_orders(family))
        kinds=[]
        for option in options:
            kind='dino4' if family=='dino' and option=='4c' else option
            if kind not in seen and (kind=='cube' or kind in SUPPORTED):
                kinds.append(kind);seen.add(kind)
        if kinds:result.append((family,tuple(kinds)))
    if seen!={'cube',*SUPPORTED}:raise ValueError('Photo entry is missing a catalogue family')
    return tuple(result)


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
    app.camera_recorded = set(getattr(screen, '_recorded', ())) if kind in ('pandora','tangram') else None
    from copy import deepcopy
    app.camera_observations=deepcopy(getattr(screen,'_ao_state',None)) if kind=='tangram' else None
    screen.manager.current = 'CameraScreen'


def _choose(title, entries, callback,back=None):
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
    popup.photo_buttons={}
    theme_popup(popup, app.theme)
    closed=[False]
    def leave(action):
        if closed[0] or not popup._is_open:return
        closed[0]=True;popup.dismiss();action()
    popup.bind(on_dismiss=lambda *_:closed.__setitem__(0,True))
    if back is not None:
        previous=UIButton(icon_name='back',size_hint_y=None,height=m.h(40))
        previous.bind(on_release=lambda *_:leave(back))
        content.add_widget(previous,index=len(content.children))
    def selected(value):
        leave(lambda:callback(value))
    for label, value in entries:
        button = UIButton(text=label, size_hint_y=None, height=m.h(56), font_size='14sp')
        button.bind(size=lambda b, *_: setattr(b, 'text_size', (b.width-m.h(8), None)))
        button.bind(on_release=lambda _, v=value: selected(v))
        grid.add_widget(button)
        popup.photo_buttons[value]=button
    popup.open()
    return popup


def choose_photo_puzzle(screen):
    def choose_kind(kind,back=None):
        orders = (2, 3, 4, 5) if kind == 'cube' else SUPPORTED[kind]
        def begin(n):
            app = App.get_running_app()
            if kind == 'cube':
                app.new_cube(n)
            elif kind == 'pandora':
                app.new_shape_cube(kind, n)
            elif kind=='tangram':
                app.new_articulated(kind)
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
            _choose(tr('camera.choose_order'), entries, begin,back=back)
    groups=photo_groups()
    def choose_family(family):
        kinds=dict(groups)[family]
        if len(kinds)==1:return choose_kind(kinds[0],back=show_root)
        from ui.screens.irregular_directory_screen import ORDER_LABELS
        entries=[(tr('camera.ordinary') if kind=='cube' else
                  tr('directory.dinosaur')+' / '+tr('directory.lattice') if kind=='dino'
                  else tr('edge.'+kind) if family=='edge_family'
                  else tr(ORDER_LABELS.get((family,'4c' if kind=='dino4' else kind),'directory.'+kind)),kind) for kind in kinds]
        return _choose(tr('directory.'+family),entries,lambda kind:choose_kind(kind,back=lambda:choose_family(family)),back=show_root)
    def show_root():
        return _choose(tr('camera.choose_puzzle'),[(tr('directory.'+family),family) for family,_ in groups],choose_family)
    return show_root()
