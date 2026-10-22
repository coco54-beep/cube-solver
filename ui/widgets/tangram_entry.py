"""Coloured shape cards, with orientation handled by the main input control."""
from kivy.app import App
from kivy.graphics import Color, Line, Mesh
from kivy.graphics.texture import Texture
from kivy.uix.widget import Widget

from ui.widgets.articulated_observation import fill
from ui.widgets.puzzle_preview import PassivePreview


class TangramPiecePreview(PassivePreview, Widget):
    """A real closed solid, with the same housings and skins as playback."""
    def __init__(self, kind, panel, palette, world, **kwargs):
        super().__init__(**kwargs)
        self.kind, self.panel, self.palette, self.world = kind, panel, palette, world
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    _white_texture = None

    @classmethod
    def white_texture(cls):
        if cls._white_texture is None:
            texture = Texture.create(size=(1, 1), colorfmt='rgba')
            def reload(target):
                target.blit_buffer(bytes((255, 255, 255, 255)), colorfmt='rgba', bufferfmt='ubyte')
            reload(texture)
            texture.add_reload_observer(reload)
            cls._white_texture = texture
        return cls._white_texture

    def redraw(self, *_):
        from cube.polyhedral import unit, cross, dot, mean
        from renderer.tangram_solids import rigid_piece_surfaces
        eye = unit((.46, .38, .8))
        right = unit(cross((0., 1., 0.), eye))
        up = cross(eye, right)
        faces = []
        for points, normal, color, *_ in rigid_piece_surfaces(self.kind, self.panel.home, self.panel.pose):
            normal = self.world.transform(*normal)
            if dot(normal, eye) <= 1e-8:continue
            points = tuple(self.world.transform(*p) for p in points)
            projected = tuple((dot(p, right), dot(p, up)) for p in points)
            rgba = self.palette[color] if color >= 0 else (.12, .15, .19, 1.)
            brightness = .8 + .2 * max(0., dot(normal, eye))
            faces.append((dot(mean(points), eye), projected,
                          tuple(c * brightness for c in rgba[:3]) + (1.,)))
        self.canvas.clear()
        if not faces:return
        xs = [x for _, points, _ in faces for x, y in points]
        ys = [y for _, points, _ in faces for x, y in points]
        factor = max(0., min((self.width-12)/max(max(xs)-min(xs), .01),
                              (self.height-12)/max(max(ys)-min(ys), .01)))
        cx, cy = (max(xs)+min(xs))/2, (max(ys)+min(ys))/2
        with self.canvas:
            for _, points, rgba in sorted(faces, key=lambda face: face[0]):
                Color(*rgba)
                vertices = [v for x, y in points for v in
                            (self.center_x+(x-cx)*factor, self.center_y+(y-cy)*factor, 0., 0.)]
                Mesh(vertices=vertices, indices=[i for j in range(1,len(points)-1) for i in (0,j,j+1)],
                     mode='triangles', texture=self.white_texture())


class TangramPanelPreview(PassivePreview, Widget):
    def __init__(self, outline, rgba, **kwargs):
        super().__init__(**kwargs)
        self.outline = outline
        self.rgba = rgba
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        factor = max(0., min((self.width - 12) / max(max(xs) - min(xs), .01),
                            (self.height - 12) / max(max(ys) - min(ys), .01)))
        points = tuple((self.center_x + (x - (max(xs) + min(xs)) / 2) * factor,
                        self.center_y + (y - (max(ys) + min(ys)) / 2) * factor)
                       for x, y in self.outline)
        with self.canvas:
            Color(*self.rgba)
            fill(points)
            Color(*App.get_running_app().theme.text)
            Line(points=[v for p in points for v in p], close=True, width=1.2)
