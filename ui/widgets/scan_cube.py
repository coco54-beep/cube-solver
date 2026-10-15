"""拍照页的小型立体预览：展示整块翻面，并允许点当前面改色。"""
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, InstructionGroup, Rectangle

from cube.coordinates import FACE_NORMALS, get_d_maxc, rc_from_pos
from renderer.cube_view import CubeView
from ui.widgets import metrics as m


class ScanCubeView(CubeView):
    def __init__(self, **kwargs):
        self._labels = None
        self._textures = {}
        self._press = None
        self.on_cell = None
        self.current_face = "F"
        super().__init__(**kwargs)
        self.lock_rotation = True
        # 与录入页一致：停稳后当前面正对镜头，立体效果由整体翻面动画呈现。
        self.camera.azimuth = 0
        self.camera.elevation = 0
        self._labels = InstructionGroup()
        self.canvas.add(self._labels)

    def set_faces(self, faces, n, world, current_face):
        from ui.screens.input_screen import _build_partial_cube
        self.current_face = current_face
        self.set_cube(_build_partial_cube(faces, n))
        self.set_whole_world(world)

    def _draw_mesh(self):
        super()._draw_mesh()
        # 未识别色格用浅灰显示；实际录入仍为空，不推测或填入默认颜色。
        for instruction in self._mesh_group.children:
            if isinstance(instruction, Color) and all(abs(c-.08) < .001 for c in instruction.rgb):
                instruction.rgba = (.25, .29, .36, 1)
        if self._labels is None:
            return
        self._labels.clear()
        if self.cube is None or self._last_proj is None or self._whole_world is None:
            return
        p = self._last_proj
        eye, right, up, forward = p["basis"]
        d, extent = get_d_maxc(self.cube.n)
        half = extent+d/2+.015
        dot = lambda a, b: sum(x*y for x, y in zip(a, b))
        for face, normal in FACE_NORMALS.items():
            normal = self._whole_world.transform(*normal)
            center = tuple(x*half for x in normal)
            if dot(normal, tuple(e-c for e, c in zip(eye, center))) <= 0:
                continue
            relative = tuple(c-e for c, e in zip(center, eye))
            depth = dot(relative, forward)
            if depth <= 0:
                continue
            x = p["widget_center_x"]+(dot(relative, right)/depth-p["center_x"])*p["pixel_scale"]
            y = p["widget_center_y"]+(dot(relative, up)/depth-p["center_y"])*p["pixel_scale"]
            font = max(10, min(self.width, self.height)*.13)
            key = (face, round(font))
            if key not in self._textures:
                label = CoreLabel(text=face, font_size=font, bold=True)
                label.refresh()
                self._textures[key] = label.texture
            texture = self._textures[key]
            w, h = texture.size
            self._labels.add(Color(.03, .05, .08, .82))
            self._labels.add(Rectangle(pos=(x-w/2-2, y-h/2), size=(w+4, h)))
            self._labels.add(Color(1, 1, 1, 1))
            self._labels.add(Rectangle(texture=texture, pos=(x-w/2, y-h/2), size=texture.size))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos) or self._whole_anim is not None:
            return False
        self._press = touch.pos
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        return touch.grab_current is self

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        press, self._press = self._press, None
        if press is None or sum((a-b)**2 for a, b in zip(press, touch.pos)) > m.h(14)**2:
            return True
        picked = self.pick_facelet(*touch.pos)
        if picked and self.on_cell and picked[1] == self.current_face and self._whole_anim is None:
            pos, face = picked
            r, c = rc_from_pos(self.cube.n, face, pos)
            self.on_cell(r, c)
        return True
