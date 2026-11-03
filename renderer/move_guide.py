"""Teaching overlay derived from the actual animation's axis and selected band."""
import math
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color,Line
from cube.polyhedral import dot,cross,unit,add,scale


def describe(cube,move):
    if cube is None or move is None:return None
    if isinstance(move,str):
        if getattr(cube,'standard_notation',False):
            from demo.formula_notation import animation_steps
            steps=animation_steps(move,cube)
        else:
            from renderer.turn import decompose_move
            steps=decompose_move(move,cube.n)
        return describe(cube,steps[0]) if steps else None
    if hasattr(move,'angle'):
        axis=tuple(1. if i==move.axis else 0. for i in range(3))
        selected={p for p in cube.cubies if p[move.axis] in move.layers}
        centre=scale(axis,sum(move.layers)/len(move.layers))
        radius=max(abs(v) for p in cube.cubies for v in p)*.8
        return axis,math.radians(move.angle),selected,centre,radius
    geometry=getattr(cube,'geometry',None)
    if geometry is None or not hasattr(move,'axis'):return None
    layers=getattr(move,'layers',()) or (move.layer,)
    selected=set().union(*(geometry.layers[move.axis][i] for i in layers))
    order=geometry.spec.turn_order;amount=move.amount%order
    if amount>order/2:amount-=order
    centre=(0.,0.,0.)
    if getattr(cube,'puzzle_kind',None) in ('siamese_a','siamese_b'):
        from cube.siamese import move_origin
        centre=move_origin(cube.puzzle_kind,move)
    elif getattr(cube,'puzzle_kind',None) in ('time_machine','bean_6','bean_10'):
        from cube.dial_beans import move_origin
        centre=move_origin(cube.puzzle_kind,move)
    return unit(geometry.spec.axes[move.axis]),math.tau*amount/order,selected,centre,.85


class MoveGuide(Widget):
    def __init__(self,view,**kwargs):
        super().__init__(size_hint=(None,None),**kwargs)
        self.view=view;self.spec=None;self.event=None;self._drawn=None
        view.bind(pos=self.sync,size=self.sync)
        view.add_widget(self);self.sync()

    def sync(self,*_):self.pos=self.view.pos;self.size=self.view.size;self.draw()

    def set_move(self,cube,move):
        self.spec=describe(cube,move);self.draw()

    def start(self):
        if self.event is None:self.event=Clock.schedule_interval(self.draw,1/30)

    def stop(self):
        if self.event:self.event.cancel();self.event=None
        self.canvas.clear();self._drawn=None

    def dispose(self):
        self.stop();self.view.unbind(pos=self.sync,size=self.sync)
        if self.parent:self.parent.remove_widget(self)

    def draw(self,*_):
        surfaces=getattr(self.view,'_last_quads',getattr(self.view,'_polygons',None))
        stamp=(self.spec,tuple(self.pos),tuple(self.size))
        if self._drawn is not None and self._drawn[0] is surfaces and self._drawn[1]==stamp:return
        self._drawn=surfaces,stamp
        self.canvas.clear()
        if self.spec is None:return
        axis,angle,selected,centre,radius=self.spec;v=self.view
        with self.canvas:
            Color(1.,.77,.12,.95)
            if hasattr(v,'_last_quads'):
                for quad,pos,face in v._last_quads:
                    if pos in selected:Line(points=[q[k] for q in quad for k in ('x','y')],close=True,width=1.4)
            elif getattr(v,'cube',None) is not None:
                for poly,slot in getattr(v,'_polygons',()):
                    if slot is not None and 0<=slot<len(v.cube.geometry.stickers) and v.cube.geometry.stickers[slot].piece in selected:
                        Line(points=[q[i]+v.pos[i] for q in poly for i in (0,1)],close=True,width=1.4)
        def project(p):
            if getattr(v,'_last_proj',None):
                proj=v._last_proj;eye,right,up,forward=proj['basis']
                world=getattr(v,'_whole_world',None)
                if world is not None:p=world.transform(*p)
                rel=add(p,scale(eye,-1));z=dot(rel,forward)
                if z<=1e-8:return None
                return (proj['widget_center_x']+(dot(rel,right)/z-proj['center_x'])*proj['pixel_scale'],
                        proj['widget_center_y']+(dot(rel,up)/z-proj['center_y'])*proj['pixel_scale'])
            if getattr(v,'_proj',None):
                eye,right,up,factor,cx,cy=v._proj
                p=add(v.observation_world().transform(*p),scale(getattr(v,'_projection_offset',(0.,0.,0.)),-1))
                return v.x+cx+dot(p,right)*factor,v.y+cy+dot(p,up)*factor
        def arrow(points):
            if any(p is None for p in points):return
            with self.canvas:
                Line(points=[x for p in points for x in p],width=1.6)
                a,b=points[-2:];dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
                if length>1:
                    dx,dy=dx/length,dy/length
                    Line(points=(b[0]-9*dx+4*dy,b[1]-9*dy-4*dx,*b,
                                 b[0]-9*dx-4*dy,b[1]-9*dy+4*dx),width=1.6)
        with self.canvas:Color(.04,.85,1.,.95)
        arrow([project(add(centre,scale(axis,s*radius))) for s in (-1.3,1.3)])
        u=unit(cross(axis,(0.,1.,0.) if abs(axis[1])<.8 else (1.,0.,0.)));w=cross(axis,u)
        arrow([project(add(centre,add(scale(u,radius*math.cos(angle*i/24)),scale(w,radius*math.sin(angle*i/24))))) for i in range(25)])
