"""Polygon renderer for the actual tetrahedral pieces, including shape changes."""

import math

from kivy.graphics import Callback, Color, ClearBuffers, ClearColor, Fbo, Mesh, Rectangle
from kivy.graphics.texture import Texture
from kivy.logger import Logger
from kivy.graphics.opengl import GL_DEPTH_TEST, GL_LEQUAL, GL_LESS, glDepthFunc, glDisable, glEnable
from kivy.uix.label import Label
from renderer.cube_view import CubeView
from renderer.mat4 import Mat4
from cube.mastermorphix import dot
from renderer.mastermorphix_mesh import oriented_piece_geometry
from renderer.polygon_visibility import Surface, painter_order
from app.constants import COLOR_INFO


_VERTEX_SHADER = """
#ifdef GL_ES
precision highp float;
#else
#define lowp
#endif
attribute vec3 surface_position;
attribute vec4 surface_color;
uniform vec2 view_size;
varying lowp vec4 fragment_color;
void main() {
    gl_Position = vec4(2.0 * surface_position.xy / view_size - 1.0,
                       surface_position.z, 1.0);
    fragment_color = surface_color;
}
"""
_FRAGMENT_SHADER = """
#ifdef GL_ES
precision mediump float;
#else
#define lowp
#endif
varying lowp vec4 fragment_color;
void main() { gl_FragColor = fragment_color; }
"""
_VERTEX_FORMAT = [(b'surface_position', 3, 'float'), (b'surface_color', 4, 'float')]


class MastermorphixView(CubeView):
    _piece_geometry = staticmethod(oriented_piece_geometry)
    def __init__(self, **kwargs):
        self.selected_pos = None
        self.recorded = None
        self.on_pick_piece = None
        self.fit_piece = False
        self.show_axes = False
        self._polygons = []
        self._pick_start = None
        self._pick_moved = False
        self._surface_fbo = None
        self._gpu_failed = False
        self._fallback_texture = None
        super().__init__(**kwargs)
        self._axis_labels = {f: Label(text=f, font_size="13sp", bold=True, size_hint=(None, None),
                                     size=(30, 26), color=(.25, .85, .95, 1), opacity=0)
                             for f in ("U", "D", "F", "B", "R", "L")}
        for label in self._axis_labels.values():
            self.add_widget(label)
        self.reset_camera()

    @staticmethod
    def _enable_depth(*args):
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

    @staticmethod
    def _disable_depth(*args):
        glDisable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

    def _ensure_surface_buffer(self):
        if self._gpu_failed:
            return False
        size = (max(1, int(self.width)), max(1, int(self.height)))
        if self._surface_fbo is None:
            # A private depth buffer avoids changing the surrounding Kivy UI.
            # Pass both stages at construction. Replacing .vs first links the
            # new vertex stage against Kivy's old fragment stage and raises.
            try:
                fbo = Fbo(size=size, with_depthbuffer=True,
                          vs=_VERTEX_SHADER, fs=_FRAGMENT_SHADER)
                if not fbo.shader.success:
                    raise RuntimeError('Mastermorphix shader compilation failed')
                with fbo:
                    Callback(self._enable_depth)
                    ClearColor(0, 0, 0, 0)
                    ClearBuffers(clear_depth=True)
                    mesh = Mesh(vertices=[], indices=[],
                                fmt=_VERTEX_FORMAT, mode='triangles')
                    Callback(self._disable_depth)
                rect = Rectangle(texture=fbo.texture)
            except Exception:
                Logger.exception('Mastermorphix: GPU initialization failed; using compatible drawing')
                self._gpu_failed = True
                return False
            self._surface_fbo, self._surface_mesh, self._surface_rect = fbo, mesh, rect
        elif self._surface_fbo.size != size:
            try:
                self._surface_fbo.size = size
            except Exception:
                Logger.exception('Mastermorphix: GPU resize failed; using compatible drawing')
                self._gpu_failed = True
                return False
        self._surface_fbo['view_size'] = (float(size[0]), float(size[1]))
        self._surface_rect.texture = self._surface_fbo.texture
        self._surface_rect.pos, self._surface_rect.size = self.pos, self.size
        self._mesh_group.add(self._surface_fbo)
        self._mesh_group.add(Color(1, 1, 1, 1))
        self._mesh_group.add(self._surface_rect)
        return True

    @staticmethod
    def _fill_fallback_texture(texture):
        texture.blit_buffer(bytes((255, 255, 255, 255)),
                            colorfmt='rgba', bufferfmt='ubyte')

    def _draw_compatible(self, surfaces):
        """Keep the page usable if a device rejects the custom GL program."""
        if self._fallback_texture is None:
            self._fallback_texture = Texture.create(size=(1, 1), colorfmt='rgba')
            self._fill_fallback_texture(self._fallback_texture)
            self._fallback_texture.add_reload_observer(self._fill_fallback_texture)
        for surface in painter_order(surfaces, (0., 0., 1.)):
            self._mesh_group.add(Color(*surface.payload))
            self._mesh_group.add(Mesh(
                vertices=[v for x, y, z in surface.vertices for v in (x, y, 0., 0.)],
                indices=list(range(len(surface.vertices))), mode='triangle_fan',
                texture=self._fallback_texture))

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
        subdivisions = 4 if self._gpu_failed else 14
        if self.cube.n > 3:
            subdivisions = max(4, round(subdivisions * 3 / self.cube.n))
        if self.fit_piece:
            points = [p for piece in self.cube.cubies.values()
                      for vertices, _, _, _, _ in self._piece_geometry(piece.home, piece.frame, subdivisions, self.cube.n)
                      for p in vertices]
            xs, ys = [dot(p, right) for p in points], [dot(p, up) for p in points]
            offset_x, offset_y = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
            scale = min(self.width, self.height)*.76/max(max(xs)-min(xs), max(ys)-min(ys), .01)
        use_gpu = self._ensure_surface_buffer()
        subdivisions = 14 if use_gpu else 4
        if self.cube.n > 3:
            subdivisions = max(4, round(subdivisions * 3 / self.cube.n))
        vertices, indices = [], []
        compatible_surfaces = []
        borders = []
        seams = []
        animation = self._anim
        moving = None
        if animation is not None:
            axis = tuple(1 if i == animation["axis"] else 0 for i in range(3))
            moving = Mat4.rotation_axis(animation["angle_current"], axis)
        light = (-.30, .80, .52)
        light_length = math.sqrt(dot(light, light))
        light = tuple(c/light_length for c in light)
        rx, ry, rz = right
        ux, uy, uz = up
        fx, fy, fz = forward
        center_x = self.center_x-offset_x*scale
        center_y = self.center_y-offset_y*scale
        self._mm_proj = (right, up, forward, scale, center_x, center_y)

        def project(point):
            # Thousands of vertices use this hot path per frame. Avoid three
            # generator-based dot products and repeated property lookups.
            x, y, z = point
            return (center_x+(x*rx+y*ry+z*rz)*scale,
                    center_y+(x*ux+y*uy+z*uz)*scale,
                    (x*fx+y*fy+z*fz)*.1)

        def append_polygon(projected, rgba, bias=0.):
            if not use_gpu:
                compatible_surfaces.append(Surface.polygon(
                    tuple((x, y, z+bias) for x, y, z in projected), rgba))
                return
            base = len(vertices)//7
            for x, y, z in projected:
                vertices.extend((x-self.x, y-self.y, z+bias, *rgba))
            for i in range(1, len(projected)-1):
                indices.extend((base, base+i, base+i+1))

        for pos, piece in self.cube.cubies.items():
            rotating = moving if moving is not None and pos in animation["positions"] else None
            for points, normal, color, finish, outline in self._piece_geometry(piece.home, piece.frame, subdivisions, self.cube.n):
                if rotating is not None:
                    normal = rotating.transform(*normal)
                if self._whole_world is not None:
                    normal = self._whole_world.transform(*normal)
                if dot(normal, forward) >= -1e-8:
                    continue
                if rotating is not None:
                    points = tuple(rotating.transform(*p) for p in points)
                if self._whole_world is not None:
                    points = tuple(self._whole_world.transform(*p) for p in points)
                if finish == "shell":
                    rgba = (.94, .955, .975, 1)
                elif self.recorded is not None and pos not in self.recorded:
                    rgba = (.38, .45, .52, 1)
                else:
                    rgba = COLOR_INFO[self.cube.palette[color]][1]
                brightness = .82 + .18 * max(0., dot(normal, light))
                rgba = tuple(c*brightness for c in rgba[:3]) + (rgba[3],)
                polygon = tuple(project(p) for p in points)
                # A small depth bias keeps coplanar stickers above the shell.
                # Android FBOs may have only a 16-bit depth buffer. The old
                # bias was below its precision and let white shell facets
                # fight with stickers. Leave several depth units of margin.
                append_polygon(polygon, rgba, -.0005 if finish == "sticker" else 0.)
                self._polygons.append((polygon, pos, color))
                if (self.cube.n > 3 or getattr(self.cube,'puzzle_kind',None)=='mirror') and finish == "sticker":
                    seams.extend((polygon[a], polygon[b]) for a, b in outline)
                if pos == self.selected_pos and finish in ("sticker", "internal"):
                    borders.extend((polygon[a], polygon[b]) for a, b in outline)

        def draw_edge(a, b, width, rgba):
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx, dy)
            if length < 1e-6:
                return
            nx, ny = -dy/length*width, dx/length*width
            append_polygon(((a[0]+nx, a[1]+ny, a[2]),
                            (a[0]-nx, a[1]-ny, a[2]),
                            (b[0]-nx, b[1]-ny, b[2]),
                            (b[0]+nx, b[1]+ny, b[2])),
                           rgba, -.0015)
        for a, b in seams:
            # Keep the ribbon above one physical pixel. Subpixel ribbons
            # disappear between pixel centers and make flat seams look dotted.
            draw_edge(a, b, .75, ((.22,.26,.32,1) if getattr(self.cube,'puzzle_kind',None)=='mirror'
                                 else (.94, .955, .975, 1)))
        for a, b in borders:
            draw_edge(a, b, 1.6, (.18, .88, 1, 1))
        if use_gpu:
            self._surface_mesh.vertices = vertices
            self._surface_mesh.indices = indices
            self._surface_fbo.ask_update()
        else:
            self._draw_compatible(compatible_surfaces)

    def pick_piece(self, x, y):
        hit = self.pick_surface(x, y)
        return hit[0] if hit is not None else None

    def pick_surface(self, x, y):
        # Interpolate depth at the tap instead of rebuilding painter order.
        nearest, picked = float('inf'), None
        for polygon, pos, color in self._polygons:
            a = polygon[0]
            for b, c in zip(polygon[1:], polygon[2:]):
                denominator = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
                if abs(denominator) < 1e-9:
                    continue
                u = ((b[1]-c[1])*(x-c[0]) + (c[0]-b[0])*(y-c[1])) / denominator
                v = ((c[1]-a[1])*(x-c[0]) + (a[0]-c[0])*(y-c[1])) / denominator
                w = 1.-u-v
                if min(u, v, w) >= -1e-7:
                    depth = u*a[2]+v*b[2]+w*c[2]
                    if depth < nearest:
                        nearest, picked = depth, pos
        if picked is None:
            return None
        right, up, forward, scale, cx, cy = self._mm_proj
        # Reconstruct the contact on a curved/offset surface, not its cubie centre.
        point = tuple(right[i]*(x-cx)/scale + up[i]*(y-cy)/scale
                      + forward[i]*nearest/.1 for i in range(3))
        return picked, point

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
    if getattr(cube, 'puzzle_kind', None) == 'mirror':
        from renderer.mirror_view import MirrorView
        return MirrorView(**kwargs)
    cls = MastermorphixView if getattr(cube, "puzzle_kind", None) == "mastermorphix" else CubeView
    return cls(**kwargs)
