"""Visual choices of complete assemblies at a Mixup entry position."""
from kivy.app import App
from kivy.graphics import Canvas,Color,Line,Rectangle
from ui.widgets.articulated_observation import OutlineCard,fill
from kivy.uix.label import Label
from ui.widgets import metrics as m


class CompositionCard(OutlineCard):
    def __init__(self,composition,**kwargs):
        self.parts=composition.parts
        super().__init__(((-1,-1),(1,-1),(1,1),(-1,1)),**kwargs)

    def redraw(self,*_):
        self.canvas.clear()
        factor=max(0,min(self.width-12,self.height-12)/2)
        theme=App.get_running_app().theme
        with self.canvas:
            Color(.1,.65,.8,.1);Rectangle(pos=self.pos,size=self.size)
            for part in self.parts:
                cx=sum(p[0] for p in part)/len(part);cy=sum(p[1] for p in part)/len(part)
                points=[(self.center_x+(cx+(x-cx)*.89)*factor,
                         self.center_y+(cy+(y-cy)*.89)*factor) for x,y in part]
                Color(.15,.65,.8,.45);fill(points)
                Color(0.,.75,.9,1) if self.active else Color(*theme.text)
                Line(points=[v for p in points for v in p],close=True,width=1.2)
            if self.active:
                Color(0.,.75,.9,1);Line(rectangle=(*self.pos,*self.size),width=1.3)


class AssemblyCard(OutlineCard):
    """A labelled drawing of all visible sides of a real typed assembly."""
    def __init__(self,diagram,label,**kwargs):
        self.diagram=diagram;self.caption=None;self._art=None
        super().__init__(((-1,-1),(1,-1),(1,1),(-1,1)),**kwargs)
        self.caption=Label(text=label,font_size='11sp',halign='center',valign='middle',size_hint=(None,None))
        self.add_widget(self.caption);self.redraw()

    def redraw(self,*_):
        # Clearing the widget canvas also removes the child Label's canvas;
        # keep diagram drawing in its own group so captions survive resizing.
        if self._art is None:
            self._art=Canvas();self.canvas.before.add(self._art)
        self._art.clear();theme=App.get_running_app().theme
        points=[p for _,poly,_ in self.diagram for p in poly]
        if not points:return
        x1=min(p[0] for p in points);x2=max(p[0] for p in points)
        y1=min(p[1] for p in points);y2=max(p[1] for p in points)
        if getattr(self.diagram,'bounds',None) is not None:x1,y1,x2,y2=self.diagram.bounds
        footer=m.h(19);factor=max(0,min((self.width-10)/max(x2-x1,.01),(self.height-footer-10)/max(y2-y1,.01)))
        cy=self.y+footer+(self.height-footer)/2
        with self._art:
            Color(.1,.65,.8,.1);Rectangle(pos=self.pos,size=self.size)
            for role,poly,marker in self.diagram:
                cxp=sum(p[0] for p in poly)/len(poly);cyp=sum(p[1] for p in poly)/len(poly)
                joined=getattr(self.diagram,'joined',False)
                inset=1. if joined or role.startswith('inner_edge') else .92
                screen=[(self.center_x+(cxp+(x-cxp)*inset-(x1+x2)/2)*factor,
                         cy+(cyp+(y-cyp)*inset-(y1+y2)/2)*factor) for x,y in poly]
                rgba=({'centre':(.12,.67,.83,.7),'edge':(.94,.58,.16,.7),
                       'inner_edge':(.65,.53,.88,1.),'inner_edge_body':(.29,.32,.40,1.)}.get(role,(.4,.5,.6,.7)))
                Color(*(rgba[:3]+(1.,) if joined else rgba))
                fill(screen);Color(*theme.text);Line(points=[v for p in screen for v in p],close=True,width=.8)
                if marker is not None:
                    length=(marker[0]**2+marker[1]**2)**.5
                    if length>1e-8:
                        dx,dy=marker[0]/length,marker[1]/length
                        cxp=sum(p[0] for p in screen)/len(screen);cyp=sum(p[1] for p in screen)/len(screen)
                        extent=min(max(p[0] for p in screen)-min(p[0] for p in screen),
                                   max(p[1] for p in screen)-min(p[1] for p in screen))*.28
                        end=(cxp+dx*extent,cyp+dy*extent)
                        Line(points=[cxp-dx*extent,cyp-dy*extent,*end],width=1.)
                        Line(points=[end[0]-(dx+dy)*extent*.5,end[1]-(dy-dx)*extent*.5,*end,
                                     end[0]-(dx-dy)*extent*.5,end[1]-(dy+dx)*extent*.5],width=1.)
            if self.active:
                Color(0.,.75,.9,1);Line(rectangle=(*self.pos,*self.size),width=1.3)
        if self.caption is not None:
            self.caption.pos=(self.x,self.y);self.caption.size=(self.width,footer)
            self.caption.text_size=self.caption.size;self.caption.color=theme.text
