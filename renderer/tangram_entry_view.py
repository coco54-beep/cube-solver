"""Physical Extreme entry; ordinary Tangram retains colour sampling."""
import math

from cube.articulated_observation import color_templates, face_world, polygon_key, project
from cube.polyhedral import CUBE, scale, dot, add
from renderer.square1_view import Square1View


class TangramEntryView(Square1View):
    """Edit real Extreme solids, or ordinary Tangram's colour sample cells.

    Face navigation rotates only the display. Extreme reuses playback's
    closed housings and inset skins, and picks using physical screen rays.
    """
    GUIDE_OFFSET = 512

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.yaw = self.pitch = self.roll = 0
        self.lock_rotation = True
        self.active_face = 2
        self.on_paint = None
        self.on_shape_point = None
        self._shape_mode = False
        self._entry_scale = 1.4
        self._draft_stamp = None
        self._entry_surfaces = ()
        self._painted = set()

    def set_draft(self, cube, state, palette, matched=False):
        self.cube = cube
        self.palette = tuple(palette)
        shape_mode = state['kind'] == 'tangram_extreme'
        if shape_mode:
            if not self._shape_mode:self.yaw, self.pitch, self.roll = 32, 22, 0
            stamp = (id(state), tuple(cube.frames), matched)
            if stamp != self._draft_stamp:
                from renderer.tangram_solids import TangramSolidPreview
                self.cancel_touch()
                self._polygons = []
                self._solid_preview = TangramSolidPreview(cube, state, matched)
                self._draft_stamp = stamp
            self._shape_mode = True
            self.pick_black_surfaces = True
            self._entry_scale = 1.05
            self._entry_surfaces = tuple((tuple(scale(p, self._entry_scale) for p in points), n, color, slot, layer, home, width)
                for points, n, color, slot, layer, home, width in self._solid_preview.surfaces(self.active_face, self.GUIDE_OFFSET))
            self.refresh()
            return
        if self._shape_mode:self.yaw = self.pitch = self.roll = 0
        self.pick_black_surfaces = False
        if state is not self._draft_stamp:
            self.cancel_touch()
            self._polygons = []
            self._shape_mode = False
            self._entry_scale = 1.4
            surfaces = []
            templates_by_face = color_templates()
            for face, templates in enumerate(templates_by_face):
                painted = {polygon_key(p['outline']): p['color'] for p in state['views'][face]}
                # A solid shell remains visible around the coloured polygons.
                shell = face_world(((-1., -1.), (1., -1.), (1., 1.), (-1., 1.)), face)
                surfaces.append((tuple(scale(p, self._entry_scale) for p in shell), CUBE[face], -1,
                                 face * 1024 + 1023, 0, 0, 1))
                for index, outline in enumerate(templates):
                    points = tuple(scale(p, self._entry_scale * 1.0004) for p in face_world(outline, face))
                    color = painted.get(polygon_key(outline), -2)
                    surfaces.append((points, CUBE[face], color, face * 1024 + index, 0, 0, 1))
            self._entry_surfaces = tuple(surfaces)
            self._draft_stamp = state
        self.refresh()

    def _surfaces(self, cube):
        return self._entry_surfaces

    def _inset(self, points):
        if self._shape_mode:return points
        centre = tuple(sum(p[a] for p in points) / len(points) for a in range(3))
        return tuple(tuple(c + (v - c) * .992 for v, c in zip(p, centre)) for p in points)

    def _is_recorded(self, slot):
        return True

    def _is_selected(self, slot):
        return slot in self._painted or slot == self.selected

    def shape_point(self, x, y):
        if not getattr(self, '_proj', None):return None
        eye, right, up, factor, cx, cy = self._proj
        view = self.observation_world()
        hit = self.pick_surface(x, y)
        if hit is not None:
            if hit[0] // 1024 != self.active_face and hit[0] % 1024 < self.GUIDE_OFFSET:return None
            axes = tuple(view.transform(*(1. if a == i else 0. for a in range(3))) for i in range(3))
            world = tuple(dot(axis, hit[1]) / self._entry_scale for axis in axes)
            return project((world,), self.active_face)[0]
        n = view.transform(*CUBE[self.active_face])
        denominator = dot(n, eye)
        if denominator < .05:return None
        offset = add(scale(right, (x - self.x - cx) / factor),
                     scale(up, (y - self.y - cy) / factor))
        position = add(offset, scale(eye, (self._entry_scale - dot(n, offset)) / denominator))
        # Observation transforms are rotations; the transpose is the inverse.
        axes = tuple(view.transform(*(1. if a == i else 0. for a in range(3))) for i in range(3))
        world = tuple(dot(axis, position) / self._entry_scale for axis in axes)
        point = project((world,), self.active_face)[0]
        return point if max(map(abs, point)) <= 1.8 else None

    def shape_ray(self, x, y):
        eye, right, up, factor, cx, cy = self._proj
        offset = add(scale(right, (x-self.x-cx)/factor), scale(up, (y-self.y-cy)/factor))
        origin = add(offset, scale(eye, 10.))
        view = self.observation_world()
        axes = tuple(view.transform(*(1. if a == i else 0. for a in range(3))) for i in range(3))
        return (tuple(dot(a, origin)/self._entry_scale for a in axes),
                tuple(-dot(a, eye)/self._entry_scale for a in axes))

    def _collect(self, start, end):
        count = max(1, int(math.hypot(end[0] - start[0], end[1] - start[1]) / 8) + 1)
        for i in range(count + 1):
            x, y = (a + (b - a) * i / count for a, b in zip(start, end))
            slot = self.pick(x, y)
            if slot is not None and slot // 1024 == self.active_face:
                self._painted.add(slot)
        self.refresh()

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if self.disabled or self._observation_animation is not None:
            return True
        if self._touch is not None:
            return True
        self._touch = touch
        self._touch_start = touch.pos
        self._touch_last = touch.pos
        self._painted = set()
        touch.grab(self)
        if not self._shape_mode:self._collect(touch.pos, touch.pos)
        return True

    def on_touch_move(self, touch):
        if touch is not self._touch:
            return False
        if self._shape_mode and not self.lock_rotation:
            self.yaw -= (touch.pos[0]-self._touch_last[0])*.4
            self.pitch = max(-80, min(80, self.pitch-(touch.pos[1]-self._touch_last[1])*.4))
        elif not self._shape_mode:self._collect(self._touch_last, touch.pos)
        self._touch_last = touch.pos
        return True

    def on_touch_up(self, touch):
        if touch is not self._touch:
            return False
        if self._shape_mode:
            tapped = sum((a - b)**2 for a, b in zip(touch.pos, self._touch_start)) < 100
            point = self.shape_point(*touch.pos) if tapped else None
            slot = self.pick(*touch.pos) if point is not None else None
            selected = slot % 1024 if slot is not None and slot // 1024 == self.active_face else None
            ray = self.shape_ray(*touch.pos) if point is not None else None
            self.cancel_touch()
            if not self.disabled and point is not None and self.on_shape_point:
                self.on_shape_point(point, selected, ray)
            return True
        self._collect(self._touch_last, touch.pos)
        slots = tuple(sorted(self._painted))
        self.cancel_touch()
        if not self.disabled and self.on_paint and slots:
            self.on_paint(slots)
        return True

    def cancel_touch(self):
        super().cancel_touch()
        self._painted = set()
        self.refresh()
