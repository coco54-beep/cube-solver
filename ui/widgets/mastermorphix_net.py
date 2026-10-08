"""A numbered tetrahedron net matching the model's four surface indices."""

from math import sqrt

from kivy.graphics import Color, InstructionGroup, Line, Triangle
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.label import Label
from kivy.uix.widget import Widget


class MastermorphixNet(Widget):
    colors = ListProperty([(0.85, .1, .1, 1), (1, .87, 0, 1),
                           (.1, .25, .85, 1), (0, .65, .2, 1)])
    selected_face = NumericProperty(-1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._diagram = InstructionGroup()
        self.canvas.before.add(self._diagram)
        self._numbers = []
        for index in range(4):
            label = Label(text=str(index+1), bold=True, font_size=sp(20),
                          size_hint=(None, None), size=(dp(36), dp(30)))
            self.add_widget(label)
            self._numbers.append(label)
        self.bind(pos=self._draw, size=self._draw, colors=self._draw, selected_face=self._draw)
        self._draw()

    def _draw(self, *_):
        self._diagram.clear()
        if self.width <= 1 or self.height <= 1 or len(self.colors) != 4:
            return
        height = sqrt(3)
        scale = .88 * min(self.width/2, self.height/height)
        ox, oy = self.center_x, self.center_y-height*scale/2
        # Face 1 contains model vertices v1 (bottom), v2 (upper left),
        # v3 (upper right). Faces 2/3/4 unfold across v2-v3/v1-v3/v1-v2.
        # These are the same indices used by cube.mastermorphix.NORMALS.
        bottom, left, right = (0, 0), (-.5, height/2), (.5, height/2)
        faces = ((bottom, right, left),
                 (left, right, (0, height)),
                 (bottom, (1, 0), right),
                 ((-1, 0), bottom, left))
        polygons = [[(ox+x*scale, oy+y*scale) for x, y in face] for face in faces]
        for index, points in enumerate(polygons):
            rgba = self.colors[index]
            self._diagram.add(Color(*rgba[:3], 1))
            self._diagram.add(Triangle(points=[v for point in points for v in point]))
            label = self._numbers[index]
            label.center = tuple(sum(p[i] for p in points)/3 for i in range(2))
            brightness = .2126*rgba[0] + .7152*rgba[1] + .0722*rgba[2]
            label.color = (.04, .07, .1, 1) if brightness > .5 else (1, 1, 1, 1)
        for points in polygons:
            self._diagram.add(Color(.04, .07, .1, .7))
            self._diagram.add(Line(points=[v for point in points for v in point], close=True, width=dp(1)))
        if 0 <= self.selected_face < 4:
            points = polygons[self.selected_face]
            self._diagram.add(Color(.15, .8, .9, 1))
            self._diagram.add(Line(points=[v for point in points for v in point], close=True, width=dp(2)))
