"""Polygon renderer for the actual tetrahedral pieces, including shape changes."""

import math

from kivy.graphics import Color, Line, Mesh
from kivy.graphics.texture import Texture
from kivy.uix.label import Label
from renderer.cube_view import CubeView
from renderer.mat4 import Mat4
from cube.mastermorphix import transform, dot
from renderer.mastermorphix_mesh import rounded_piece_geometry, piece_outline_indices
from renderer.polygon_visibility import Surface, painter_order, plane
from app.constants import COLOR_INFO


def _inside(point, polygon):
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            if x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1]) + a[0]:
                inside = not inside
    return inside


class MastermorphixView(CubeView):
    def __init__(self, **kwargs):
        self.selected_pos = None
        self.recorded = None
        self.on_pick_piece = None
        self.fit_piece = False
        self.show_axes = False
        self._polygons = []
        self._pick_start = None
        self._pick_moved = False
        # Mesh must bind an opaque texture instead of inheriting a label atlas.
        self._surface_texture = Texture.create(size=(1, 1), colorfmt="rgba")
        self._fill_surface_texture(self._surface_texture)
        self._surface_texture.add_reload_observer(self._fill_surface_texture)
        super().__init__(**kwargs)
        self._axis_labels = {f: Label(text=f, font_size="13sp", bold=True, size_hint=(None, None),
                                     size=(30, 26), color=(.25, .85, .95, 1), opacity=0)
                             for f in ("U", "D", "F", "B", "R", "L")}
        for label in self._axis_labels.values():
            self.add_widget(label)
        self.reset_camera()

    @staticmethod
    def _fill_surface_texture(texture):
        # Android may recreate the graphics context after the app resumes.
        texture.blit_buffer(bytes((255, 255, 255, 255)),
                            colorfmt="rgba", bufferfmt="ubyte")

    def reset_camera(self):
        """Use a symmetric tetrahedron view with a level base and upright tip."""
        # Looking along (1, 1, 1) presents three equally visible faces. With
        # world Y up, the two bottom vertices have identical screen heights.
        self.camera.azimuth = 45.0
        self.camera.elevation = math.degrees(math.atan(1.0 / math.sqrt(2.0)))
        self.camera.distance = 9.0
        self.camera.target = (0, 0, 0)
        self._display_zoom = 1.0
        self._redraw()

    def _draw_mesh(self):
        if not hasattr(self, "_mesh_group"):
            return
        self._mesh_group.clear()
        self._polygons = []
        if self.cube is None or self.width <= 1 or self.height <= 1:
            return
        basis = self._get_camera_basis()
        if basis is None:
            return
        _, right, up, forward = basis
        scale = min(self.width, self.height) * .15 * self._display_zoom
        if hasattr(self, "_axis_labels"):
            from cube.coordinates import FACE_NORMALS
            for face, label in self._axis_labels.items():
                axis = FACE_NORMALS[face]
                if self._whole_world is not None:
                    axis = self._whole_world.transform(*axis)
                label.opacity = 1 if self.show_axes and dot(axis, forward) < -.1 else 0
                sx, sy = dot(axis, right), dot(axis, up)
                if sx*sx + sy*sy < .01:
                    # A front-facing axis projects to the center of the piece.
                    # Keep its label below the model instead of on the colors.
                    label.center = (self.center_x, self.center_y-scale*2.6)
                else:
                    label.center = (self.center_x+sx*scale*2.9,
                                    self.center_y+sy*scale*2.9)
        offset_x = offset_y = 0
        if self.fit_piece:
            points = [transform(piece.frame, p) for piece in self.cube.cubies.values()
                      for vertices, _, _ in rounded_piece_geometry(piece.home) for p in vertices]
            xs, ys = [dot(p, right) for p in points], [dot(p, up) for p in points]
            offset_x, offset_y = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
            scale = min(self.width, self.height)*.76/max(max(xs)-min(xs), max(ys)-min(ys), .01)
        surfaces = []
        animation = self._anim
        moving = None
        if animation is not None:
            axis = tuple(1 if i == animation["axis"] else 0 for i in range(3))
            moving = Mat4.rotation_axis(animation["angle_current"], axis)
        light = (-.30, .80, .52)
        light_length = math.sqrt(dot(light, light))
        light = tuple(c/light_length for c in light)
        for pos, piece in self.cube.cubies.items():
            for (points, color, finish), outline in zip(rounded_piece_geometry(piece.home),
                                                        piece_outline_indices(piece.home)):
                points = [transform(piece.frame, p) for p in points]
                if moving is not None and pos in animation["positions"]:
                    points = [moving.transform(*p) for p in points]
                if self._whole_world is not None:
                    points = [self._whole_world.transform(*p) for p in points]
                surface_plane = plane(points)
                if surface_plane is None or dot(surface_plane[0], forward) >= -1e-8:
                    continue
                if finish == "internal":
                    rgba = (.085, .10, .13, 1)
                elif finish == "shell":
                    rgba = (.94, .955, .975, 1)
                elif self.recorded is not None and pos not in self.recorded:
                    rgba = (.38, .45, .52, 1)
                else:
                    rgba = COLOR_INFO[self.cube.palette[color]][1]
                brightness = .82 + .18 * max(0., dot(surface_plane[0], light))
                rgba = tuple(c*brightness for c in rgba[:3]) + (rgba[3],)
                surfaces.append(Surface(tuple(points), tuple((points[a], points[b]) for a, b in outline),
                                        (rgba, pos, color, finish)))

        def project(point):
            return (self.center_x + (dot(point, right)-offset_x)*scale,
                    self.center_y + (dot(point, up)-offset_y)*scale)

        for surface in painter_order(surfaces, forward):
            rgba, pos, color, finish = surface.payload
            polygon = [project(p) for p in surface.vertices]
            self._mesh_group.add(Color(*rgba))
            # The canvas shader uses Kivy's default position/UV attributes.
            self._mesh_group.add(Mesh(
                vertices=[value for x, y in polygon for value in (x, y, 0., 0.)],
                indices=list(range(len(polygon))), mode="triangle_fan",
                texture=self._surface_texture,
            ))
            selected = pos == self.selected_pos
            if selected and finish in ("sticker", "internal"):
                self._mesh_group.add(Color(.18, .88, 1, 1))
                for a, b in surface.edges:
                    self._mesh_group.add(Line(points=[*project(a), *project(b)], width=1.6))
            self._polygons.append((polygon, pos, color))

    def pick_piece(self, x, y):
        for polygon, pos, color in reversed(self._polygons):
            if _inside((x, y), polygon):
                return pos
        return None

    def cancel_touch(self):
        touch = self._touch0
        self._touch0 = None
        self._touch0_pos = None
        self._pick_start = None
        self._pick_moved = False
        if touch is not None:
            touch.ungrab(self)

    def on_touch_down(self, touch):
        # A locked input view still accepts taps; dragging must not orbit it.
        if self.lock_rotation and self.on_pick_piece is not None and self.collide_point(*touch.pos):
            if getattr(touch, "is_mouse_scrolling", False):
                return super().on_touch_down(touch)
            if self._touch0 is not None or self._whole_anim is not None:
                return True
            self._touch0 = touch
            self._touch0_pos = touch.pos
            self._pick_start = touch.pos
            self._pick_moved = False
            touch.grab(self)
            return True
        handled = super().on_touch_down(touch)
        if touch is self._touch0:
            self._pick_start = touch.pos
            self._pick_moved = False
        return handled

    def on_touch_move(self, touch):
        if touch is self._touch0:
            if self._pick_start is not None and sum((a-b)**2 for a, b in zip(self._pick_start, touch.pos)) >= 144:
                self._pick_moved = True
            if self.lock_rotation:
                return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        start = self._pick_start if touch is self._touch0 else None
        moved = self._pick_moved
        handled = super().on_touch_up(touch)
        if start is not None:
            self._pick_start = None
            self._pick_moved = False
            if not moved and sum((a-b)**2 for a, b in zip(start, touch.pos)) < 144:
                pos = self.pick_piece(*touch.pos)
                if pos is not None and self.on_pick_piece is not None:
                    self.on_pick_piece(pos)
        return handled


def cube_view_for(cube=None, **kwargs):
    cls = MastermorphixView if getattr(cube, "puzzle_kind", None) == "mastermorphix" else CubeView
    return cls(**kwargs)
