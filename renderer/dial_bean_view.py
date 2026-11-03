"""Standard batched 3D renderer, with live labels on numbered ring pieces."""
import math
from kivy.uix.label import Label
from renderer.polyhedral_view import PolyhedralView,PolyhedralTwistView


class Labels:
    def set_cube(self,cube):
        for label in getattr(self,'_number_labels',{}).values():self.remove_widget(label)
        self._number_labels={}
        super().set_cube(cube)
        if cube.puzzle_kind=='time_machine':
            for i in range(24,96):
                label=Label(text='',size_hint=(None,None),size=(24,22),font_size='12sp',bold=True,
                            color=(.04,.05,.06,1),outline_width=1,outline_color=(.9,.9,.9,.8))
                self.add_widget(label);self._number_labels[i]=label
        else:
            self.yaw=0;self.pitch=10;self.fit_margin=1.0

    def _draw(self,*args):
        super()._draw(*args)
        if self.cube is None:return
        for label in self._face_labels:label.opacity=0
        labels=getattr(self,'_number_labels',{})
        for label in labels.values():label.opacity=0
        groups={}
        for points,index in getattr(self,'_number_polygons',self._polygons):
            if index in labels:groups.setdefault(index,[]).extend(points)
        for index,points in groups.items():
            value=self.cube.colors[index]
            if not 0<=value<72:continue
            label=labels[index];label.text=str(value%12+1)
            label.center=(self.x+sum(p[0] for p in points)/len(points),self.y+sum(p[1] for p in points)/len(points))
            label.opacity=1


class DialBeanView(Labels,PolyhedralView):pass
class DialBeanTwistView(Labels,PolyhedralTwistView):
    def _rotor_hit(self,x,y):
        from cube.polyhedral import dot
        if not self.cube or self.cube.puzzle_kind not in ('bean_6','bean_10'):return None
        from cube.dial_beans import petals
        p=petals(self.cube.puzzle_kind);r=.235 if p==3 else .36
        eye,right,up,factor,cx,cy=self._proj;world=self.observation_world()
        for side,sign in ((0,1),(1,-1)):
            if dot(world.transform(0,0,sign),eye)<=1e-8:continue
            def project(point):
                point=world.transform(*point)
                return self.x+cx+factor*dot(point,right),self.y+cy+factor*dot(point,up)
            poly=[project((r*math.cos(i*math.tau/30),r*math.sin(i*math.tau/30),sign*.21)) for i in range(30)]
            signs=[(b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]) for a,b in zip(poly,poly[1:]+poly[:1])]
            if min(signs)>=-1e-7 or max(signs)<=1e-7:
                return 3*p+side,project((0,0,sign*.21))

    def on_touch_down(self,touch):
        if self.collide_point(*touch.pos) and getattr(self,'_rotor_grab',None) is not None:return True
        if (self.cube and self.cube.puzzle_kind in ('bean_6','bean_10') and
                self.collide_point(*touch.pos) and self.lock_view and self._move is None and
                not self.camera_busy and self._grab is None):
            self._draw();hit=self._rotor_hit(*touch.pos)
            if hit is not None:
                axis,centre=hit;self.selected_turn_axis=axis
                callback=getattr(self,'on_control_select',None)
                if callback:callback(axis)
                self._rotor_grab=(touch,tuple(touch.pos),axis,centre)
                touch.grab(self);return True
        return super().on_touch_down(touch)

    def on_touch_move(self,touch):
        grab=getattr(self,'_rotor_grab',None)
        if grab is not None and grab[0] is touch:return True
        return super().on_touch_move(touch)

    def on_touch_up(self,touch):
        grab=getattr(self,'_rotor_grab',None)
        if grab is None or grab[0] is not touch:return super().on_touch_up(touch)
        _,start,axis,centre=grab;self._rotor_grab=None;touch.ungrab(self)
        from ui.widgets import metrics as m
        dx,dy=touch.x-start[0],touch.y-start[1]
        if math.hypot(dx,dy)>=m.h(18) and self.on_twist:
            from cube.polyhedral import Move,dot
            rx,ry=start[0]-centre[0],start[1]-centre[1]
            sense=(rx*dy-ry*dx) if math.hypot(rx,ry)>m.h(6) else dx-dy
            normal=self.observation_world().transform(*self.cube.geometry.spec.axes[axis])
            if dot(normal,self._proj[0])<0:sense=-sense
            spec=self.cube.geometry.spec
            self.on_twist(Move(axis,0,(spec.step(axis)*(1 if sense>=0 else -1))%spec.turn_order))
        return True

    def cancel_touch(self):
        grab=getattr(self,'_rotor_grab',None)
        if grab is not None:grab[0].ungrab(self)
        self._rotor_grab=None
        super().cancel_touch()

    def reset_camera(self):
        super().reset_camera()
        if self.cube and self.cube.puzzle_kind in ('bean_6','bean_10'):
            self.yaw=0;self.pitch=8
