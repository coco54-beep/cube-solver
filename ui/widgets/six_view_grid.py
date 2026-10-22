"""Flat observation grid: a drag outlines one visible physical panel."""
from kivy.app import App
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.widget import Widget
from cube.cuboid_observation import UNKNOWN, EMPTY, PLASTIC


class SixViewGrid(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.draft = None; self.face = 2; self.palette = (); self.selection = ()
        self.on_region = None; self._first = None; self._last = None; self._touch = None
        self.bind(pos=self.redraw, size=self.redraw)
        app = App.get_running_app()
        if app is not None:
            app.theme.bind(on_palette=self.redraw)

    def set_draft(self, draft, face, palette):
        self.cancel_touch(); self.draft = draft; self.face = face; self.palette = palette
        self.selection = (); self.redraw()

    def _metrics(self):
        width, height = self.draft.model['shapes'][self.face]
        size = min((self.width-16)/width, (self.height-16)/height)
        return width, height, max(1, size), self.center_x-width*size/2, self.center_y-height*size/2

    def hit(self, x, y):
        if self.draft is None:
            return None
        w, h, size, left, bottom = self._metrics()
        c, r = int((x-left)//size), h-1-int((y-bottom)//size)
        return r*w+c if 0 <= r < h and 0 <= c < w else None

    def redraw(self, *_):
        self.canvas.clear()
        if self.draft is None:
            return
        theme = App.get_running_app().theme
        w, h, size, left, bottom = self._metrics()
        samples = self.draft.views[self.face]
        with self.canvas:
            for i, (value, group, depth) in enumerate(samples):
                r, c = divmod(i, w); x = left+c*size; y = bottom+(h-1-r)*size
                color = (self.palette[value] if value >= 0 else (.055, .065, .08, 1) if value == PLASTIC else
                         theme.bg if value == EMPTY else tuple(theme.text[:3])+(.14,))
                Color(*color); Rectangle(pos=(x, y), size=(size, size))
                if value == UNKNOWN:
                    Color(*theme.text[:3], .2)
                    Line(points=[x+size*.36, y+size*.5, x+size*.64, y+size*.5], width=1)
                if value == EMPTY:
                    Color(*theme.text[:3], .22)
                    for dx, dy in ((.28, .28), (.72, .72)):
                        Rectangle(pos=(x+size*dx, y+size*dy), size=(1.5, 1.5))
                Color(*theme.text[:3], .18)
                Line(rectangle=(x, y, size, size), width=.6)
                # Heavy boundaries record cut seams, not artificial sample cells.
                Color(.10, .15, .19, 1)
                for neighbour, line in ((i+1 if c+1 < w else None, [x+size, y, x+size, y+size]),
                                         (i+w if r+1 < h else None, [x, y, x+size, y])):
                    if value not in (EMPTY, UNKNOWN) and (neighbour is None or samples[neighbour][0] != value or samples[neighbour][1] != group):
                        Line(points=line, width=1.5)
                if i in self.selection:
                    Color(0, .8, .95, .23); Rectangle(pos=(x, y), size=(size, size))
                    Color(0, .8, .95, 1); Line(rectangle=(x, y, size, size), width=1.1)
            Color(*theme.text[:3], .6)
            Line(rectangle=(left, bottom, w*size, h*size), width=1)

    def on_touch_down(self, touch):
        if self.disabled or not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        index = self.hit(*touch.pos)
        if index is None:
            return super().on_touch_down(touch)
        touch.grab(self); self._touch = touch; self._first = self._last = index
        self.selection = (index,); self.redraw(); return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)
        index = self.hit(*touch.pos)
        if index is not None:
            self._last = index
            self.selection = self.draft.rectangle(self.face, self._first, index)
            self.redraw()
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)
        region = tuple(self.selection); touch.ungrab(self); self._touch = None
        self._first = self._last = None
        if self.on_region is not None:
            self.on_region(region)
        return True

    def cancel_touch(self):
        if self._touch is not None:
            self._touch.ungrab(self); self._touch = None
        self._first = self._last = None
