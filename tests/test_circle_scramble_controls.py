"""Exercise real entry buttons, including repeated scrambles and undo."""
from types import SimpleNamespace

import pytest

from tests.test_bandaged_manual_controls import pump, until
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, NoTransition
from app.theme import Theme
from cube.circle_cube import Circle2Cube, KINDS
from cube.dial_beans import KINDS as DIAL_BEANS
from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble
from ui.screens.polyhedral_screen import PolyhedralScreen


@pytest.fixture
def entry(monkeypatch, request):
    kind, size = request.param
    cube = Circle2Cube() if kind == 'circle_2' else PolyhedralPuzzle(kind, DIAL_BEANS.get(kind, 3))
    cube.colors = [-1] * len(cube.colors)
    app = SimpleNamespace(cube=cube, theme=Theme(), polyhedral_solution=None,
                          puzzle_kind=kind, n=cube.n, simple_input=True)
    monkeypatch.setattr(App, 'get_running_app', staticmethod(lambda: app))
    previous_size = Window.size
    Window.size = size
    manager = ScreenManager(transition=NoTransition())
    screen = PolyhedralScreen(name='PolyhedralScreen')
    manager.add_widget(screen)
    Window.add_widget(manager)
    for _ in range(4):
        pump()
    yield screen, cube
    screen.reset_interaction()
    Window.remove_widget(manager)
    Window.size = previous_size
    pump()


CASES = [(kind, size) for kind in ('circle_2',) + KINDS + tuple(DIAL_BEANS)
         for size in ((800, 600), (390, 844))]


@pytest.mark.parametrize('entry', CASES, indirect=True)
def test_random_button_repeats_and_undo_restores_the_entire_state(entry, monkeypatch):
    screen, cube = entry
    calls = []

    def seeded(work, length):
        calls.append(len(calls) + 10)
        return scramble(work, length, seed=calls[-1])

    monkeypatch.setattr('cube.polyhedral_scramble.scramble', seeded)
    button = screen.entry_action_buttons['random']
    row = button.parent
    assert row is screen.entry_action_buttons['solve'].parent
    assert row is screen.entry_action_buttons['undo'].parent
    assert not hasattr(row,'more')
    assert screen.entry_action_buttons['target'].parent is None
    # Dispatch the actual bound action rather than calling randomize directly.
    button.dispatch('on_release')
    assert len(calls) == 1 and not button.disabled and not cube.is_solved()
    assert all(c >= 0 for c in cube.colors)
    first = cube.clone()
    button.dispatch('on_release')
    assert len(calls) == 2 and not button.disabled and cube.colors != first.colors
    replay = cube.clone()
    for move in reversed(cube.scramble_history):
        replay.apply_move(move.inverse(cube.geometry.spec.turn_order))
    assert replay.is_solved()
    screen.entry_action_buttons['undo'].dispatch('on_release')
    assert cube.colors == first.colors
    if cube.puzzle_kind == 'circle_2':
        assert cube.anchor == first.anchor
    if cube.puzzle_kind.startswith(('circle_', 'crazy_')):
        assert cube.circle_history == first.circle_history


@pytest.mark.parametrize('entry', [('circle_2', (390, 844))], indirect=True)
def test_failed_generation_preserves_input_and_allows_retry(entry, monkeypatch):
    screen, cube = entry
    screen.choose_color(2)
    screen.paint(0)
    before = cube.clone()

    def fail(work, length):
        work.colors[0] = 5
        raise RuntimeError('test generation failure')

    monkeypatch.setattr('cube.polyhedral_scramble.scramble', fail)
    button = screen.entry_action_buttons['random']
    button.dispatch('on_release')
    assert cube.colors == before.colors and cube.anchor == before.anchor
    assert not button.disabled and screen._job is None
    monkeypatch.setattr('cube.polyhedral_scramble.scramble',
                        lambda work, length: scramble(work, length, seed=21))
    button.dispatch('on_release')
    assert all(c >= 0 for c in cube.colors) and not cube.is_solved()


@pytest.mark.parametrize('entry', [(kind, (390, 844)) for kind in DIAL_BEANS], indirect=True)
def test_simple_tools_are_visible_directly_without_secondary_menu(entry):
    screen, cube = entry
    row = screen.entry_action_buttons['random'].parent
    assert not hasattr(row,'open_more')
    assert all(button.icon_name and not button.text for button in screen.entry_action_buttons.values())
    for key in ('twist','random','clear','undo','solve'):
        assert screen.entry_action_buttons[key].parent is row
    for key in ('target',):
        assert screen.entry_action_buttons[key].parent is not row
    assert screen.entry_action_buttons['random'].parent is row
    assert not row.disabled


@pytest.mark.parametrize('entry', [(kind, (390, 844)) for kind in DIAL_BEANS], indirect=True)
def test_face_caption_tracks_the_animated_observation_face(entry):
    from ui.widgets.dial_bean_controls import input_hint
    screen, cube = entry
    face = screen._face
    before = screen.hint.text
    assert before == input_hint(screen)
    screen.btn_next.dispatch('on_release')
    until(lambda: not screen._view_busy)
    assert screen._face != face and screen.hint.text != before
    assert screen.hint.text == input_hint(screen)
    screen.btn_prev.dispatch('on_release')
    until(lambda: not screen._view_busy)
    assert screen._face == face and screen.hint.text == before


@pytest.mark.parametrize('entry', [('time_machine', (390, 844))], indirect=True)
def test_number_selection_uses_highlight_and_paints_without_rebuilding_controls(entry):
    screen, cube = entry
    buttons = tuple(screen._number_buttons)
    buttons[11].dispatch('on_release')
    assert screen._dial_number == 11
    assert buttons[11].active and not any(b.disabled for b in buttons)
    screen._swatches[2].dispatch('on_release')
    screen.paint(24)
    screen.paint(25)
    assert cube.colors[24:26] == [35, 24]
    assert tuple(screen._number_buttons) == buttons
    assert [i for i, b in enumerate(buttons) if b.active] == [1]
    screen.entry_action_buttons['undo'].dispatch('on_release')
    assert cube.colors[25] == -1 and screen._dial_number == 0
    assert [i for i, b in enumerate(screen._number_buttons) if b.active] == [0]


@pytest.mark.parametrize('entry', [('time_machine', (390, 844))], indirect=True)
def test_outer_corner_and_inner_corner_share_real_pick_colour_and_undo(entry):
    from tests.test_bandaged_manual_controls import Tap
    screen, cube = entry
    view = screen.view
    view._draw()
    patches = [polygon for polygon, slot in view._polygons if slot == 0]
    assert len(patches) == len(cube.geometry.stickers[0].patches) > 1

    def tap(polygon):
        point = (view.x + sum(p[0] for p in polygon)/len(polygon),
                 view.y + sum(p[1] for p in polygon)/len(polygon))
        assert view.pick(*point) == 0
        touch = Tap(point)
        assert view.on_touch_down(touch) and view.on_touch_up(touch)

    screen._number_buttons[7].dispatch('on_release')
    screen._swatches[2].dispatch('on_release')
    tap(patches[-1])
    assert cube.colors[0] == 74 and screen._dial_number == 7
    assert cube.colors[24:] == [-1]*72
    screen._swatches[5].dispatch('on_release')
    tap(patches[0])
    assert cube.colors[0] == 77
    screen.entry_action_buttons['undo'].dispatch('on_release')
    assert cube.colors[0] == 74 and screen._dial_number == 7


@pytest.mark.parametrize('entry', [(kind, (390, 844)) for kind in ('bean_6','bean_10')], indirect=True)
def test_real_twist_page_has_independent_rotors_and_tracks_side_and_undo(entry):
    from cube.dial_beans import petals,goal
    from ui.screens.polyhedral_screen import PolyhedralTwistScreen
    screen,cube=entry;cube.colors=list(goal(cube.puzzle_kind));p=petals(cube.puzzle_kind)
    manager=screen.manager;twist=PolyhedralTwistScreen(name='PolyhedralTwistScreen');manager.add_widget(twist)
    screen.open_twist();pump();assert manager.current==twist.name
    assert len(twist.axis.values)==3*p+2 and 'CF' in twist.axis.values[3*p] and 'CB' in twist.axis.values[3*p+1]
    half=len(cube.colors)//2;before=list(cube.colors)
    twist._select_control_axis(3*p);twist.turn(1);until(lambda:twist.view._move is None)
    front=list(cube.colors)
    assert front[:half]!=before[:half] and front[half:]==before[half:]
    twist.change_view(1);until(lambda:not twist.view.camera_busy)
    assert twist._axis==3*p+1
    twist.turn(1);until(lambda:twist.view._move is None);both=list(cube.colors)
    assert both[:half]==front[:half] and both[half:]!=front[half:]
    twist.undo();until(lambda:twist.view._move is None);assert cube.colors==front
    twist.redo();until(lambda:twist.view._move is None);assert cube.colors==both
    twist.back();assert manager.current==screen.name and screen._cube.colors==both
