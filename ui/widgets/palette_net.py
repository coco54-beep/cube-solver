"""Numbered six-face reference for shape-puzzle colour settings."""
from kivy.graphics import Color,Rectangle,Line
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
