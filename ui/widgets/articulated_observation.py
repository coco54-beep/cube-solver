"""Flat polygon entry, outline cards and a provisional observation preview."""
from kivy.app import App
from kivy.graphics import Color,Line,Mesh,Rectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from cube.articulated_observation import contains,normal,polygon_key
from cube.polyhedral import CUBE,add,scale,dot
from renderer.square1_view import Square1View


def fill(points):
    Mesh(vertices=[v for p in points for v in (*p,0.,0.)],
         indices=[i for j in range(1,len(points)-1) for i in (0,j,j+1)],mode='triangles')


class ObservationBoard(Widget):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.items=[];self.pending=None;self.region=None;self.palette=();self.on_point=None;self.on_region=None;self.face=2
        self.templates=();self.fill_mode=False;self.allow_regions=True;self.on_stroke=None;self._stroke=[]
        self._touch=None;self._start=None
        self.bind(pos=self.redraw,size=self.redraw)

    def metrics(self):return min(self.width,self.height)/(2.2 if self.fill_mode else 3.8),self.center_x,self.center_y
    def screen(self,p):
        factor,x,y=self.metrics();return x+p[0]*factor,y+p[1]*factor
    def world(self,p):
        factor,x,y=self.metrics()
        return tuple(max(-1.8,min(1.8,v)) for v in ((p[0]-x)/max(factor,1),(p[1]-y)/max(factor,1)))

    def redraw(self,*_):
        self.canvas.clear();theme=App.get_running_app().theme
        with self.canvas:
            for outline in self.templates:
                points=tuple(self.screen(p) for p in outline)
                Color(*theme.text[:3],.12);fill(points)
                Color(*theme.text[:3],.25);Line(points=[v for p in points for v in p],close=True,width=.65)
            if not self.fill_mode:
                Color(*theme.text[:3],.09)
                for v in (-1.,0.,1.):
                    Line(points=[*self.screen((-1.75,v)),*self.screen((1.75,v))],width=.6)
                    Line(points=[*self.screen((v,-1.75)),*self.screen((v,1.75))],width=.6)
            for item in sorted(self.items,key=lambda p:sum(dot(v,CUBE[self.face]) for v in p['preview'])/len(p['preview'])):
                points=tuple(self.screen(p) for p in item['outline'])
                Color(*self.palette[item['color']]);fill(points)
                Color(.05,.07,.09,1);Line(points=[v for p in points for v in p],close=True,width=1.3)
            if self.pending is not None:
                points=tuple(self.screen(p) for p in self.pending)
                Color(0.,.8,.95,.35);fill(points)
                Color(0.,.8,.95,1);Line(points=[v for p in points for v in p],close=True,width=2)
            if self.region is not None:
                x1,y1,x2,y2=self.region;a=self.screen((x1,y1));b=self.screen((x2,y2))
                Color(0.,.75,.9,1);Line(rectangle=(*a,b[0]-a[0],b[1]-a[1]),width=1.1,dash_length=5,dash_offset=3)
            if self.fill_mode and self._stroke:
                Color(0.,.8,.95,.7);Line(points=[v for p in self._stroke for v in self.screen(p)],width=2)

    def on_touch_down(self,touch):
        if self.disabled or not self.collide_point(*touch.pos):return super().on_touch_down(touch)
        touch.grab(self);self._touch=touch;self._start=touch.pos;self._stroke=[self.world(touch.pos)];return True
    def on_touch_move(self,touch):
        if touch.grab_current is not self:return super().on_touch_move(touch)
        if self.fill_mode:
            self._stroke.append(self.world(touch.pos));self.redraw();return True
        if self.allow_regions and sum((a-b)**2 for a,b in zip(touch.pos,self._start))>100:
            a=self.world(self._start);b=self.world(touch.pos)
            self.region=(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]));self.redraw()
        return True
    def on_touch_up(self,touch):
        if touch.grab_current is not self:return super().on_touch_up(touch)
        start=self._start;touch.ungrab(self);self._touch=None;self._start=None
        if self.fill_mode:
            points=tuple(self._stroke+[self.world(touch.pos)]);self._stroke=[]
            if self.on_stroke:self.on_stroke(points)
            self.redraw()
        elif self.allow_regions and sum((a-b)**2 for a,b in zip(touch.pos,start))>100:
            if self.on_region:self.on_region(self.region)
        elif self.on_point:self.on_point(self.world(touch.pos))
        return True
    def cancel_touch(self):
        if self._touch:self._touch.ungrab(self)
        self._touch=self._start=None;self._stroke=[]


class OutlineCard(ButtonBehavior,Widget):
    def __init__(self,outline,active=False,**kwargs):
        super().__init__(**kwargs);self.outline=outline;self.active=active
        self.bind(pos=self.redraw,size=self.redraw);self.redraw()
    def redraw(self,*_):
        self.canvas.clear()
        xs=[p[0] for p in self.outline];ys=[p[1] for p in self.outline]
        factor=min((self.width-12)/max(max(xs)-min(xs),.01),(self.height-12)/max(max(ys)-min(ys),.01))
        points=[(self.center_x+(x-(max(xs)+min(xs))/2)*factor,self.center_y+(y-(max(ys)+min(ys))/2)*factor) for x,y in self.outline]
        with self.canvas:
            Color(.1,.65,.8,.1);Rectangle(pos=self.pos,size=self.size)
            Color(.15,.65,.8,.45);fill(points)
            Color(0.,.75,.9,1) if self.active else Color(*App.get_running_app().theme.text)
            Line(points=[v for p in points for v in p],close=True,width=1.5)
            if self.active:Line(rectangle=(*self.pos,*self.size),width=1.3)


class ObservationPreview(Square1View):
    """Unmatched panels are only a provisional preview, never a cube state."""
    panels=();pending=None;matched=False;piece_filter=None
    def _is_recorded(self,slot):return True
    def _inset(self,points):return points
    def _surfaces(self,cube):
        if self.matched:
            from renderer.articulated_view import ArticulatedView
            return ArticulatedView._surfaces(self,cube)
        seen=set();result=[]
        for world,color in list(self.panels)+([self.pending] if self.pending else []):
            key=color,polygon_key(world)
            if key in seen:continue
            seen.add(key);n=normal(world)
            result.append((world,n,color,0,0,0,1))
            # Thin reverse housing keeps a recorded tilted panel visible from
            # behind without inventing a sticker colour on its back.
            back=tuple(add(p,scale(n,-.015)) for p in reversed(world))
            result.append((back,scale(n,-1),-1,0,0,0,1))
        return tuple(result)
