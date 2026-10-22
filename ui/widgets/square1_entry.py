"""Touch-friendly layer diagrams for Square-1 colour and block entry."""
from kivy.clock import Clock
from kivy.graphics import Color,Line,Mesh,Rectangle
from kivy.core.text import Label as CoreLabel
from kivy.uix.widget import Widget
from renderer.square1_view import _ring
from renderer.polyhedral_view import CUBE_PALETTE
from ui.widgets.buttons import UIButton


class Square1ColorButton(UIButton):
    fill_color=(.37,.43,.5,1)

    def _button_color(self):
        return self.fill_color

    def _pressed_color(self):
        return self.fill_color

    def set_color(self,color):
        self.fill_color=CUBE_PALETTE[color] if color>=0 else (.37,.43,.5,1)
        self.color=(.08,.13,.17,1) if color in (0,3,4) else (1,1,1,1)
        self._rebuild()


def _inside(point,polygon):
    x,y=point
    inside=False
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside=not inside
    return inside


class Square1Ring(Widget):
    def __init__(self,layer,on_select,**kwargs):
        super().__init__(**kwargs)
        self.layer=layer
        self.on_select=on_select
        self.entry=None
        self.selected=(0,0)
        self._hits=[]
        self._trigger=Clock.create_trigger(self._draw,0)
        self.bind(pos=self._trigger,size=self._trigger)

    def refresh(self,entry,selected):
        self.entry,self.selected=entry,selected
        self._trigger()

    def _draw(self,*args):
        self.canvas.clear()
        self._hits=[]
        if self.entry is None:
            return
        def ring_outline(layer,start,width,piece):
            if hasattr(self.entry,'outline'):
                return self.entry.outline(layer,start,width,piece)
            return _ring(layer,start,width)
        extent=max((abs(value) for layer,start,width,piece in self.entry.groups() if layer==self.layer
                    for point in ring_outline(layer,start,width,piece) for value in point),default=1.)
        radius=min(self.width,self.height)*.43/max(1.,extent)
        def project(points):
            direction=-(self.entry.layer_direction(self.layer) if hasattr(self.entry,'layer_direction') else
                        (1 if self.layer==0 else -1))
            return tuple((self.center_x+x*radius,self.center_y+y*radius*direction) for x,y in points)
        def polygon(points,color):
            with self.canvas:
                Color(*(CUBE_PALETTE[color] if color>=0 else (.55,.60,.65,1)))
                Mesh(vertices=[v for x,y in points for v in (x,y,0.,0.)],
                     indices=list(range(len(points))),mode='triangle_fan')
        for slot in range(12):
            if self.entry.slots[self.layer*12+slot]>=0:
                continue
            points=project(ring_outline(self.layer,slot,1,-1))
            polygon(points,-2)
            with self.canvas:
                Color(.25,.32,.38,.65)
                Line(points=[v for p in points for v in p],close=True,width=.6,dash_length=3,dash_offset=2)
                if self.selected[0]==self.layer*12+slot:
                    Color(0,.75,.86,1)
                    Line(points=[v for p in points for v in p],close=True,width=2)
            self._hits.append((points,self.layer*12+slot,0))
        for layer,start,width,piece in self.entry.groups():
            if layer!=self.layer:
                continue
            slot=layer*12+start
            outline=ring_outline(layer,start,width,piece)
            points=project(outline)
            inner=project(tuple((x*.80,y*.80) for x,y in outline))
            cap,sides=self.entry.piece_colors(piece)
            polygon(points,cap)
            self._hits.append((points,slot,0))
            for field,(a,b) in enumerate(zip(outline[1:],outline[2:]),1):
                band=project(((a[0]*.80,a[1]*.80),(b[0]*.80,b[1]*.80),b,a))
                polygon(band,sides[field-1])
                self._hits.append((band,slot,field))
                if self.selected[0]==slot:
                    label=CoreLabel(text=str(field),font_size=12,color=(.08,.15,.22,1)
                                    if sides[field-1] in (0,3,4) else (1,1,1,1))
                    label.refresh()
                    x=sum(p[0] for p in band)/4
                    y=sum(p[1] for p in band)/4
                    with self.canvas:
                        Color(1,1,1,1)
                        Rectangle(texture=label.texture,pos=(x-label.texture.width/2,y-label.texture.height/2),
                                  size=label.texture.size)
                if self.selected==(slot,field):
                    with self.canvas:
                        Color(0,.75,.86,1)
                        Line(points=[v for p in band for v in p],close=True,width=1.5)
            with self.canvas:
                Color(.12,.18,.24,1)
                Line(points=[v for p in points for v in p],close=True,width=.8)
                if self.selected==(slot,0):
                    Color(0,.75,.86,1)
                    Line(points=[v for p in inner for v in p],close=True,width=1.5)
        # A permanent start line and arrow make both layer diagrams unambiguous.
        import math
        start=project(ring_outline(self.layer,0,1,-1))[1]
        finish=project(ring_outline(self.layer,1,1,-1))[-1]
        a=(self.center_x+(start[0]-self.center_x)*1.10,self.center_y+(start[1]-self.center_y)*1.10)
        b=(self.center_x+(finish[0]-self.center_x)*1.10,self.center_y+(finish[1]-self.center_y)*1.10)
        angle=math.atan2(b[1]-a[1],b[0]-a[0])
        with self.canvas:
            Color(0,.75,.86,1)
            Line(points=[self.center_x,self.center_y,*a],width=1.2)
            Line(points=[*a,*b],width=1.2)
            Line(points=[b[0]-7*math.cos(angle-.5),b[1]-7*math.sin(angle-.5),*b,
                         b[0]-7*math.cos(angle+.5),b[1]-7*math.sin(angle+.5)],width=1.2)

    def on_touch_down(self,touch):
        if self.collide_point(*touch.pos):
            for polygon,slot,field in reversed(self._hits):
                if _inside(touch.pos,polygon):
                    self.on_select(slot,field)
                    return True
        return super().on_touch_down(touch)
