"""Small colour/number controls using the existing entry layout."""
from app.i18n import tr
from ui.widgets import metrics as m
from ui.widgets.buttons import UIButton
from ui.screens.mastermorphix_screen import _Swatch


def select_number(screen, number):
    screen._dial_number = number % 12
    for i, button in enumerate(screen._number_buttons):
        button.active = i == screen._dial_number


def choose_number(screen,number):
    if not screen.entry_can_edit() or screen._cube.puzzle_kind!='time_machine':return
    select_number(screen,number)


def build_palette(screen):
    rows=[screen.palette,screen.palette2]+screen._extra_palette_rows
    for i,row in enumerate(rows):
        row.clear_widgets()
        visible = i < 3  # Colours, then numbers 1–6 and 7–12.
        row._height_px = 44 if visible else 0
        row.height = m.h(row._height_px)
        row.opacity = int(visible)
        row.disabled = not visible
    screen._swatches=[];screen._number_buttons=[]
    for face in range(6):
        button=_Swatch(screen.view.palette[72+face],text=str(face+1),active=face==screen._color)
        button.bind(on_release=lambda *_,v=face:screen.choose_color(v))
        rows[0].add_widget(button);screen._swatches.append(button)
    for number in range(12):
        button=UIButton(text=str(number+1),active=number==getattr(screen,'_dial_number',0))
        button.bind(on_release=lambda *_,v=number:choose_number(screen,v))
        rows[1+number//6].add_widget(button)
        screen._number_buttons.append(button)
    select_number(screen,getattr(screen,'_dial_number',0))


def input_hint(screen):
    kind = screen._cube.puzzle_kind
    if kind == 'time_machine':
        code = ('U','R','F','D','L','B')[screen._face]
        face = tr('face.'+code)
    else:
        code = 'F' if screen._face == 2 else 'B'
        face = tr('dial.front_side' if code == 'F' else 'dial.back_side')
    return tr('input.face',face=face,code=code)+'\n'+tr('poly.'+kind+'_input')


def axis_labels(kind):
    if kind=='time_machine':
        return tuple(f'{face} · {tr("dial.core")} 90°' for face in ('U','R','F','D','L','B'))+tuple(
            f'{face} · {tr("dial.ring")} 30°' for face in ('U','R','F','D','L','B'))
    from cube.dial_beans import petals
    p=petals(kind)
    return tuple(f'{"F" if side==0 else "B"}{j+1} · {tr("dial.front" if side==0 else "dial.back")} · 36°' for side in range(2) for j in range(p))+tuple(
        f'W{j+1} · {tr("dial.wing")} · 180°' for j in range(p))+tuple(
        f'C{side} · {tr("dial.rotor_front" if side=="F" else "dial.rotor_back")}' for side in ('F','B'))
