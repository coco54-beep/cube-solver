"""Input Extreme through the actual model, cards and face navigation."""
import os
import random
from time import monotonic, sleep
from types import SimpleNamespace

import pytest

os.environ.setdefault('KIVY_NO_ARGS', '1')
os.environ.setdefault('KIVY_METRICS_DENSITY', '1')
os.environ.setdefault('KIVY_DPI', '96')
from app.desktop_runtime import configure_graphics
configure_graphics()
pytest.importorskip('kivy')
from kivy.config import Config
Config.set('graphics', 'window_state', 'hidden')
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from app.theme import Theme
from cube.articulated import ArticulatedCube
from cube.articulated_observation import (
    ObservationDraft, _panels, _depth, centre2, contains, face_world,
    polygon_key, colored_outlines_at,
)
from cube.polyhedral import dot
from ui.screens.articulated_screen import ArticulatedEntryScreen


def wait_until(predicate, seconds=12):
    deadline = monotonic() + seconds
    while not predicate() and monotonic() < deadline:
        Clock.tick()
        Builder.sync()
        Clock.tick_draw()
        Builder.sync()
        Window.flip()
        sleep(.005)
    assert predicate()


def scrambled(seed):
    cube = ArticulatedCube('tangram_extreme')
    rng = random.Random(seed)
    previous = None
    for _ in range(16 if seed else 0):
        choices = list(cube.moves())
        rng.shuffle(choices)
        for move in choices:
            if (move.axis, move.layer) == previous:
                continue
            if rng.randrange(2):
                move = move.inverse(cube.geometry.spec.turn_order)
            try:
                cube.apply_move(move)
            except ValueError:
                continue
            previous = move.axis, move.layer
            break
    return cube


def signature(cube):
    return sorted((color, polygon_key(points))
                  for home in range(len(cube.solids))
                  for points, color in cube.placed_faces(home) if color >= 0)


@pytest.fixture
def editor(monkeypatch):
    app = SimpleNamespace(theme=Theme(), cube=ArticulatedCube('tangram_extreme'),
                          polyhedral_solution=None)
    monkeypatch.setattr(App, 'get_running_app', staticmethod(lambda: app))
    screen = ArticulatedEntryScreen()
    previous_size = Window.size
    Window.add_widget(screen)
    screen.on_pre_enter()
    yield screen
    screen.reset_interaction()
    Window.remove_widget(screen)
    Window.size = previous_size
    Clock.tick()


class Tap:
    def __init__(self, pos):
        self.pos = pos

    def grab(self, widget):
        self.owner = widget

    def ungrab(self, widget):
        self.owner = None


def tap_point(screen, point, world=None):
    view = screen.view
    view._draw()
    eye, right, up, factor, cx, cy = view._proj
    world = face_world((point,), screen._ao_face)[0] if world is None else world
    world = view.observation_world().transform(*(v * view._entry_scale for v in world))
    pos = (view.x + cx + dot(world, right) * factor,
           view.y + cy + dot(world, up) * factor)
    touch = Tap(pos)
    prior_groups = screen._color_layout.shapes.groups
    assert view.on_touch_down(touch)
    assert view.on_touch_up(touch)
    wait_until(lambda: screen._job is None)
    assert screen._color_layout.shapes.groups is not prior_groups, (screen._ao_face, point, world, view.shape_point(*pos), view.pick_surface(*pos), view.yaw, view.pitch)
    return screen._color_layout.shapes


def choose_target(screen, item):
    shapes = screen._color_layout.shapes
    target = polygon_key(item['outline'])
    found = next(((gi, vi) for gi, group in enumerate(shapes.groups)
                  for vi, option in enumerate(group)
                  if option['color'] == item['color'] and polygon_key(option['outline']) == target
                  and (not option.get('physical') or 'preview' not in item or
                       any(polygon_key(p.world) == polygon_key(item['preview']) for p in option['panels']))), None)
    assert found is not None, (screen._ao_face, item, screen._message)
    group, variant = found
    shapes.change_page(group // shapes.PAGE_SIZE - shapes.page)
    cards = list(reversed(shapes.gallery.children))
    cards[group % shapes.PAGE_SIZE].dispatch('on_release')
    for _ in range(len(shapes.groups[group])):
        if shapes.group == group and shapes.variant == variant:break
        screen._color_layout.rotate_button.dispatch('on_release')
    assert shapes.group == group and shapes.variant == variant
    assert any(polygon_key(p['outline']) == target and p['color'] == item['color']
               for p in screen._ao_state['views'][screen._ao_face])


def visible_point(cube, face, item):
    panels = [p for h, pose in enumerate(cube.frames) for p in _panels(cube, h, pose, face)]
    panel = next(p for p in panels if p.color == item['color']
                 and polygon_key(p.outline) == polygon_key(item['outline']))
    centre = centre2(panel.outline)
    witnesses = [centre] + [tuple(.8 * v + .2 * c for v, c in zip(p, centre))
                            for p in panel.outline]
    return next(p for p in witnesses if all(other is panel or not contains(other.outline, p)
                or _depth(other, p, face) <= _depth(panel, p, face) + 1e-6 for other in panels))


def test_blank_model_tap_opens_colour_shape_cards_and_highlights(editor):
    screen = editor
    for _ in range(4):
        Clock.tick()
    item = ObservationDraft.from_cube(screen._cube).views[screen._ao_face][0]
    shapes = tap_point(screen, centre2(item['outline']))
    assert shapes.groups
    assert screen.view.selected is not None
    assert screen.view.selected % 1024 >= screen.view.GUIDE_OFFSET
    assert shapes.gallery.height > 0 and not shapes.gallery.disabled
    choose_target(screen, item)
    before = screen._ao_state
    screen.undo()
    assert screen._ao_state != before and not any(screen._ao_state['views'])


@pytest.mark.parametrize('seed,size', [(0, (800, 600)), (37, (390, 844)), (91, (800, 600))])
def test_six_faces_enter_from_blank_and_match_without_history(editor, seed, size):
    source = scrambled(seed)
    target = ObservationDraft.from_cube(source)
    screen = editor
    Window.size = size
    screen.size = size
    for _ in range(4):
        Clock.tick()
    assert screen._root_layout.body.orientation == ('horizontal' if size[0] > size[1] * 1.1 else 'vertical')
    # Front view is a public camera option, not a flattened geometry model.
    screen._color_layout.view_button.dispatch('on_release')
    assert screen.view.yaw == screen.view.pitch == 0
    for _ in range(6):
        face = screen._ao_face
        entered = set()
        for item in target.views[face]:
            point = visible_point(source, face, item)
            panel = next(p for h, pose in enumerate(source.frames) for p in _panels(source, h, pose, face)
                         if p.color == item['color'] and polygon_key(p.outline) == polygon_key(item['outline']))
            world = list(face_world((point,), face)[0])
            axis = (1, 0, 2, 1, 0, 2)[face]
            world[axis] *= _depth(panel, point, face)
            tap_point(screen, point, world)
            picked = screen._color_layout.shapes.key
            choose_target(screen, item)
            entered.add((polygon_key(item['outline']), item['color']))
            observed = {(polygon_key(p['outline']), p['color']) for p in screen._ao_state['views'][face]}
            assert entered <= observed, ('lost previous input', face, entered-observed, item, picked)
        if _ < 5:
            screen._color_layout.change_face(1)
            assert screen._busy_turn
            assert not screen.entry_can_edit()
            wait_until(lambda: not screen._busy_turn)
    assert not screen._applied()
    assert not screen._cube.history
    screen.apply()
    wait_until(lambda: screen._job is None)
    assert screen._applied(), screen._message
    assert not screen._cube.history
    assert signature(screen._cube) == signature(source)


def test_reselect_recolour_rotate_and_undo_keep_neighbour_panels(editor):
    screen = editor
    for _ in range(4):
        Clock.tick()
    face = screen._ao_face
    target = ObservationDraft.from_cube(screen._cube).views[face]
    first = target[0]
    tap_point(screen, centre2(first['outline']))
    choose_target(screen, first)
    shapes = tap_point(screen, centre2(first['outline']))
    variants = len(shapes.groups[shapes.group])
    before = screen._ao_state
    for _ in range(variants):
        screen._color_layout.rotate_button.dispatch('on_release')
    assert screen._ao_state == before
    neighbour = target[1]
    tap_point(screen, centre2(neighbour['outline']))
    choose_target(screen, neighbour)
    before = screen._ao_state
    shapes = tap_point(screen, centre2(first['outline']))
    alternate = next(option for group in shapes.groups for option in group
                     if option['color'] != first['color']
                     and polygon_key(option['outline']) == polygon_key(first['outline']))
    choose_target(screen, alternate)
    old_key = polygon_key(first['outline'])
    for f in range(6):
        assert [p for p in screen._ao_state['views'][f] if f != face or polygon_key(p['outline']) != old_key] == [
            p for p in before['views'][f] if f != face or polygon_key(p['outline']) != old_key]
    screen.undo()
    assert screen._ao_state == before


def test_all_colour_gallery_contains_each_visible_scrambled_panel():
    cube = scrambled(91)
    for face, items in enumerate(ObservationDraft.from_cube(cube).views):
        for item in items:
            options = colored_outlines_at(cube.puzzle_kind, face, centre2(item['outline']))
            assert any(option['color'] == item['color'] and
                       polygon_key(option['outline']) == polygon_key(item['outline']) for option in options)


def test_occupied_neighbour_cannot_be_overwritten_or_append_a_panel(editor):
    screen = editor
    screen.assign_initial()
    for _ in range(4):Clock.tick()
    shapes = tap_point(screen, (.2, .2))
    before = screen._ao_state
    count = sum(map(len, before['views']))
    from cube.articulated_observation import panels_for_outline
    neighbour = next(p for p in before['views'][screen._ao_face] if polygon_key(p['outline']) != shapes.key[1])
    option = dict(neighbour, panels=panels_for_outline(screen._cube.puzzle_kind, screen._ao_face, polygon_key(neighbour['outline'])))
    undo_count = len(screen._ao_undo)
    assert not shapes.commit(option)
    assert screen._ao_state is before
    assert sum(map(len, screen._ao_state['views'])) == count == 66
    assert len(screen._ao_undo) == undo_count
    assert screen._message
    assert screen._applied()


def test_tapping_black_housing_border_selects_panel_without_adding(editor):
    screen = editor
    for _ in range(4):Clock.tick()
    item = ObservationDraft.from_cube(screen._cube).views[screen._ao_face][0]
    tap_point(screen, centre2(item['outline']))
    choose_target(screen, item)
    centre = centre2(item['outline'])
    edge = tuple((a+b)/2 for a, b in zip(item['outline'][0], item['outline'][1]))
    point = tuple(a + .002*(b-a) for a, b in zip(edge, centre))
    shapes = tap_point(screen, point)
    assert shapes.key == (screen._ao_face, polygon_key(item['outline']))
    alternate = next(option for choices in shapes.groups for option in choices
                     if option['color'] != item['color'] and polygon_key(option['outline']) == polygon_key(item['outline']))
    choose_target(screen, alternate)
    assert sum(map(len, screen._ao_state['views'])) == 1


def test_direction_button_can_change_a_real_multi_direction_shape(editor):
    screen = editor
    for _ in range(4):Clock.tick()
    shapes = tap_point(screen, (.75, .75))
    group = next(i for i, choices in enumerate(shapes.groups)
                 if len(choices) > 1 and all(shapes.fits(option) for option in choices))
    shapes.choose(group)
    assert not screen._color_layout.rotate_button.disabled
    before = polygon_key(shapes.selected_item()['outline'])
    screen._color_layout.rotate_button.dispatch('on_release')
    assert polygon_key(shapes.selected_item()['outline']) != before
    for _ in range(len(shapes.groups[group]) - 1):
        screen._color_layout.rotate_button.dispatch('on_release')
    assert polygon_key(shapes.selected_item()['outline']) == before


def test_matched_entry_uses_the_playback_solids_and_normals(editor):
    from renderer.articulated_view import ArticulatedView
    from cube.polyhedral import scale
    screen = editor
    cube = scrambled(37)
    screen._cube = cube
    screen.entry_commit_state()
    expected = [(polygon_key(tuple(scale(p, screen.view._entry_scale) for p in points)),
                 tuple(round(v, 6) for v in normal), color == -1)
                for home in range(len(cube.solids))
                for points, normal, color, *_ in ArticulatedView.piece_surfaces(cube, home)]
    actual = [(polygon_key(points), tuple(round(v, 6) for v in normal), color == -1)
              for points, normal, color, *_ in screen.view._surfaces(cube)]
    assert sorted(actual) == sorted(expected)
    assert any(sum(abs(v) > .01 for v in normal) > 1 for _, normal, _ in actual)
    assert len(screen.view._solid_preview.bodies) == len(cube.solids)
    assert screen.view.yaw == 32 and screen.view.pitch == 22
    before = screen._ao_state
    screen._color_layout.view_button.dispatch('on_release')
    assert screen.view.yaw == screen.view.pitch == 0
    assert screen._ao_state is before
    assert screen.view._surfaces(cube) == screen.view._entry_surfaces
    screen._color_layout.view_button.dispatch('on_release')
    assert screen.view.yaw == 32 and screen.view.pitch == 22
    assert screen._ao_state is before


def test_unlocked_3d_orbit_changes_only_the_camera(editor):
    screen = editor
    for _ in range(4):Clock.tick()
    view = screen.view
    before = screen._ao_state
    view.lock_rotation = False
    touch = Tap(view.center)
    view.on_touch_down(touch)
    yaw, pitch = view.yaw, view.pitch
    touch.pos = touch.pos[0] + 30, touch.pos[1] + 20
    view.on_touch_move(touch)
    view.on_touch_up(touch)
    assert view.yaw != yaw and view.pitch != pitch
    assert screen._ao_state is before
    assert not any(screen._ao_state['views'])
