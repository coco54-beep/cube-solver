"""Numbered six-face reference for shape-puzzle colour settings."""
from kivy.graphics import Color,Rectangle,Line,Mesh
import math
from kivy.properties import ListProperty,NumericProperty
from kivy.uix.label import Label
from kivy.uix.widget import Widget


class CubePaletteNet(Widget):
    colors=ListProperty([])
    labels=ListProperty([])
    selected_face=NumericProperty(0)
    # Palette order is U, R, F, D, L, B.
    _cells=((1,2),(2,1),(1,1),(1,0),(0,1),(3,1))

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._labels=[]
        for i in range(6):
            label=Label(text=str(i+1),font_size='18sp',size_hint=(None,None))
            self._labels.append(label);self.add_widget(label)
        self.bind(pos=self._draw,size=self._draw,colors=self._draw,labels=self._draw,selected_face=self._draw)

    def _draw(self,*args):
        self.canvas.before.clear()
        if len(self.colors)!=6:return
        unit=min(self.width/4.4,self.height/3.4)
        ox,oy=self.center_x-2*unit,self.center_y-1.5*unit
        for i,(column,row) in enumerate(self._cells):
            rgba=self.colors[i];x,y=ox+column*unit,oy+row*unit
            with self.canvas.before:
                Color(*rgba);Rectangle(pos=(x+1,y+1),size=(unit-2,unit-2))
                if self.selected_face==i:
                    Color(0,.75,.86,1);Line(rectangle=(x+2,y+2,unit-4,unit-4),width=2)
            label=self._labels[i];label.size=(unit,unit);label.pos=(x,y)
            label.text=self.labels[i] if len(self.labels)==6 else str(i+1)
            luminance=.2126*rgba[0]+.7152*rgba[1]+.0722*rgba[2]
            label.color=(.04,.07,.1,1) if luminance>.5 else (1,1,1,1)


class PolygonPaletteNet(Widget):
    """Numbered facet reference that fits the available width and height."""
    colors=ListProperty([])
    labels=ListProperty([])
    selected_face=NumericProperty(0)

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._labels=[]
        for i in range(12):
            label=Label(text=str(i+1),font_size='16sp',size_hint=(None,None))
            self._labels.append(label);self.add_widget(label)
        self.bind(pos=self._draw,size=self._draw,colors=self._draw,labels=self._draw,selected_face=self._draw)

    def _draw(self,*args):
        self.canvas.before.clear()
        count=len(self.colors)
        while len(self._labels)<count:
            label=Label(text=str(len(self._labels)+1),font_size='16sp',size_hint=(None,None))
            self._labels.append(label);self.add_widget(label)
        for label in self._labels:label.opacity=0
        if not count:return
        aspect=max(1.,self.width)/max(1.,self.height)
        columns=min(count,8,max(1,math.ceil(math.sqrt(count*aspect))))
        rows=math.ceil(count/columns)
        cell=min(self.width/(columns+.4),self.height/(rows+.4))
        ox=self.center_x-columns*cell/2;oy=self.center_y-rows*cell/2
        sides=3 if count==8 else 5
        for i,rgba in enumerate(self.colors):
            x=ox+(i%columns+.5)*cell;y=oy+(rows-i//columns-.5)*cell
            points=tuple((x+cell*.44*math.sin(j*math.tau/sides),
                          y+cell*.44*math.cos(j*math.tau/sides)) for j in range(sides))
            with self.canvas.before:
                Color(*rgba)
                Mesh(vertices=[v for px,py in points for v in (px,py,0.,0.)],indices=list(range(sides)),mode='triangle_fan')
                Color(*((0,.75,.86,1) if self.selected_face==i else (.15,.2,.25,1)))
                Line(points=[v for p in points+(points[0],) for v in p],width=2 if self.selected_face==i else 1)
            label=self._labels[i];label.pos=(x-cell/2,y-cell/2);label.size=(cell,cell);label.opacity=1
            label.font_size=max(8.,min(16.,cell*.36))
            label.text=self.labels[i] if len(self.labels)==count else str(i+1)
            label.color=(.04,.07,.1,1) if sum(a*b for a,b in zip(rgba,(.2126,.7152,.0722)))>.5 else (1,1,1,1)
