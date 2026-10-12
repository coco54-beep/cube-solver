"""Solid, shape-changing Square-1 pieces and legal slice animations."""
import math
from functools import lru_cache

from kivy.clock import Clock
from kivy.graphics import Color,Mesh
from kivy.graphics.texture import Texture

from cube.polyhedral import add,scale,dot,cross,unit,rotate,mean,CUBE,clip,key
from cube.square1 import Square1Cube,piece_colors
from renderer.polyhedral_view import PolyhedralView,CUBE_PALETTE,_VERTEX_FORMAT
from renderer.mat4 import Mat4


def _ring(layer,start,width):
    direction=1 if layer==0 else -1
    angle=math.radians(-15+direction*start*30)
    end=angle+direction*math.radians(width*30)
    r=1/math.cos(math.pi/12)
    points=[(0.,0.),(r*math.sin(angle),r*math.cos(angle))]
    if width==2:
        mid=(angle+end)/2
        points.append((math.sqrt(2)*math.sin(mid),math.sqrt(2)*math.cos(mid)))
    points.append((r*math.sin(end),r*math.cos(end)))
    return tuple(points)


@lru_cache(maxsize=16)
def _piece_colors(piece):
    return piece_colors(piece)


def surfaces(cube):
    result=[]
    for layer,start,width,piece in cube.groups():
        outline=_ring(layer,start,width)
        low,high=(.27,1.1) if layer==0 else (-1.1,-.27)
        bottom=tuple((x,low,z) for x,z in outline)
        top=tuple((x,high,z) for x,z in outline)
        cap,sides=cube.piece_colors(piece) if getattr(cube,'color_entry',False) else _piece_colors(piece)
        polygons=[(top,cap if layer==0 else -1,0),(bottom,cap if layer==1 else -1,0)]
        for i,(a,b) in enumerate(zip(outline,outline[1:]+outline[:1])):
            color=sides[i-1] if 1<=i<len(outline)-1 else -1
            polygons.append((((a[0],low,a[1]),(b[0],low,b[1]),
                              (b[0],high,b[1]),(a[0],high,a[1])),color,i))
        centre=mean(top+bottom)
        slot=layer*12+start
        for points,color,field in polygons:
            normal=unit(cross(add(points[1],scale(points[0],-1)),add(points[2],scale(points[0],-1))))
            if dot(normal,add(mean(points),scale(centre,-1)))<0:
                normal=scale(normal,-1)
            selected=(slot,field) if getattr(cube,'color_entry',False) else slot
            result.append((points,normal,color,selected,layer,start,width))
    # The two halves of the middle bar retain their orientation independently
    # of top/bottom turns and flip with every slash.
    for half in (0,1):
        # The slash plane cuts an ordinary square middle layer. Rotating a
        # rectangular half in its own coordinate frame would leave a gap.
        rot=math.radians(75)
        axis=(math.sin(rot),0.,math.cos(rot))
        other=(math.cos(rot),0.,-math.sin(rot))
        box=[(x,y,z) for x,y,z in ((-1.,-.25,-1.),(1.,-.25,-1.),(1.,.25,-1.),(-1.,.25,-1.),
                                  (-1.,-.25,1.),(1.,-.25,1.),(1.,.25,1.),(-1.,.25,1.))]
        polygons=[]
        seam={}
        for indices in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)):
            points=clip(tuple(box[i] for i in indices),scale(axis,1 if half==0 else -1),0.)
            if not points:
                continue
            polygons.append(points)
            for p in points:
                if abs(dot(axis,p))<1e-7:
                    seam[key(p)]=p
        cap=sorted(seam.values(),key=lambda p:math.atan2(p[1],dot(p,other)))
        if half==1:
            cap.reverse()
        polygons.append(tuple(cap))
        centre=mean(tuple(p for poly in polygons for p in poly))
        for points in polygons:
            normal=unit(cross(add(points[1],scale(points[0],-1)),add(points[2],scale(points[0],-1))))
            if dot(normal,add(mean(points),scale(centre,-1)))<0:
                normal=scale(normal,-1)
            color=max((1,2,4,5),key=lambda i:dot(CUBE[i],normal)) if abs(normal[1])<.5 and max(abs(normal[0]),abs(normal[2]))>.999 else -1
            if half==0 and cube.middle:
                points=tuple(rotate(p,axis,math.pi) for p in points)
                normal=rotate(normal,axis,math.pi)
            result.append((points,normal,color,24+half,2,half,1))
    return tuple(result)


class Square1View(PolyhedralView):
    recorded=None
    fit_piece=False
    show_middle=True
    camera_target=(0.,0.,0.)
    _surfaces=staticmethod(surfaces)

    def _inset(self,points):
        centre=mean(points)
        return tuple(add(centre,scale(add(p,scale(centre,-1)),.989)) for p in points)

    def _is_recorded(self,slot):
        return self.recorded is None or slot>=24 or self.cube.slots[slot] in self.recorded

    def _motion(self,points,normal,slot,layer,start,width):
        if self._move is None:
            return points,normal
        move=self._move
        if move.axis<2:
            moving=layer==move.axis
            axis=(0.,1.,0.)
            amount=move.amount%12
            if amount>6:
                amount-=12
            angle=math.radians(-amount*30 if move.axis==0 else amount*30)*self._fraction
        else:
            moving=(layer==0 and start>=6) or (layer==1 and start<6) or (layer==2 and start==0)
            axis=(math.sin(math.radians(75)),0.,math.cos(math.radians(75)))
            angle=math.pi*self._fraction
        if moving:
            return tuple(rotate(p,axis,angle) for p in points),rotate(normal,axis,angle)
        return points,normal

    def set_cube(self,cube):
        self.cancel_animation()
        self.cube=cube
        self.palette=CUBE_PALETTE
        self._trigger()

    def reset_camera(self):
        self.yaw,self.pitch,self.roll=32,22,0
        self.set_whole_world(Mat4())
        self.refresh()

    def animate_move(self,move,on_done=None,duration=.3):
        if self._move is not None or self.cube is None or (move.axis==2 and not self.cube.can_slice()):
            return False
        self._move=move
        self._fraction=0
        elapsed=0.
        def tick(dt):
            nonlocal elapsed
            elapsed+=dt
            self._fraction=min(1.,elapsed/max(.01,duration))
            self._draw()
            if self._fraction>=1:
                self.cube.apply_move(move)
                self._move=self._event=None
                self.refresh()
                if on_done:
                    on_done()
                return False
        self._event=Clock.schedule_interval(tick,1/24)
        return True

    def _draw(self,*args):
        if self.cube is None or self.width<2 or self.height<2:
            return
        yaw,pitch=math.radians(self.yaw),math.radians(self.pitch)
        eye=(math.sin(yaw)*math.cos(pitch),math.sin(pitch),math.cos(yaw)*math.cos(pitch))
        right=unit(cross((0,1,0),eye))
        up=cross(eye,right)
        if self.roll:
            angle=math.radians(self.roll)
            right,up=(add(scale(right,math.cos(angle)),scale(up,math.sin(angle))),
                      add(scale(up,math.cos(angle)),scale(right,-math.sin(angle))))
        factor=min(self.width,self.height)*.25
        cx,cy=self.width/2,self.height/2
        faces=self._surfaces(self.cube)
        if not self.show_middle:
            faces=tuple(s for s in faces if s[4]<2)
        if self.fit_piece and faces:
            points=[p for surface in faces for p in surface[0]]
            xs,ys=[dot(p,right) for p in points],[dot(p,up) for p in points]
            factor=min(self.width,self.height)*.82/max(max(xs)-min(xs),max(ys)-min(ys),.01)
            cx-=(max(xs)+min(xs))/2*factor
            cy-=(max(ys)+min(ys))/2*factor
        self._proj=(eye,right,up,factor,cx,cy)
        observation=self.observation_world()
        if not self.fit_piece:
            target=observation.transform(*self.camera_target)
            cx-=dot(target,right)*factor
            cy-=dot(target,up)*factor
            self._proj=(eye,right,up,factor,cx,cy)
        vertices,indices,compatible=[],[],[]
        self._polygons=[]
        light=unit((-.3,.8,.52))
        for points,normal,color,slot,layer,start,width in faces:
            points,normal=self._motion(points,normal,slot,layer,start,width)
            points=tuple(observation.transform(*p) for p in points)
            normal=observation.transform(*normal)
            if dot(normal,eye)<=1e-8:
                continue
            rgba=self.palette[color] if color>=0 else ((.37,.43,.5,1) if color==-2 else (.12,.15,.19,1))
            if color>=0 and not self._is_recorded(slot):
                rgba=(.37,.43,.5,1)
            centre=mean(points)
            points=self._inset(points)
            brightness=.82+.18*max(0,dot(normal,light))
            shade=tuple(v*brightness for v in rgba[:3])+(1,)
            if slot==self.selected:
                shade=tuple(.75*v+.25*c for v,c in zip(shade,(0.,.9,1.,1.)))
            projected=tuple((cx+dot(p,right)*factor,cy+dot(p,up)*factor,-dot(p,eye)*.12) for p in points)
            if color>=0 or color==-2:
                self._polygons.append((projected,slot))
            base=len(vertices)//7
            for x,y,z in projected:
                vertices.extend((x,y,z,*shade))
            for i in range(1,len(projected)-1):
                indices.extend((base,base+i,base+i+1))
            compatible.append((projected,shade))
        if self._buffer():
            if not self._meshes:
                mesh=Mesh(vertices=[],indices=[],fmt=_VERTEX_FORMAT,mode='triangles')
                self._group.add(mesh)
                self._meshes.append(mesh)
            self._meshes[0].vertices=vertices
            self._meshes[0].indices=indices
            self._fbo.ask_update()
        else:
            if not hasattr(self,'_fallback_texture'):
                self._fallback_texture=Texture.create(size=(1,1),colorfmt='rgba')
                def fill(texture):
                    texture.blit_buffer(bytes((255,255,255,255)),colorfmt='rgba',bufferfmt='ubyte')
                fill(self._fallback_texture)
                self._fallback_texture.add_reload_observer(fill)
            self._compatible.clear()
            for points,rgba in sorted(compatible,key=lambda item:mean(item[0])[2],reverse=True):
                self._compatible.add(Color(*rgba))
                self._compatible.add(Mesh(vertices=[v for x,y,z in points for v in (x+self.x,y+self.y,0.,0.)],
                                         indices=list(range(len(points))),mode='triangle_fan',texture=self._fallback_texture))
