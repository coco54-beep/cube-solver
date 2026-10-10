"""Depth-buffered, batched rendering and picking of polyhedral facelets."""
import math
from functools import lru_cache

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Callback,ClearBuffers,ClearColor,Color,Fbo,Mesh,Rectangle
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics.opengl import GL_DEPTH_TEST,GL_LEQUAL,GL_LESS,glDepthFunc,glEnable,glDisable
from kivy.properties import NumericProperty,BooleanProperty
from kivy.logger import Logger
from kivy.graphics.texture import Texture
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from cube.polyhedral import dot,cross,unit,mean,add,scale,rotate,key,body,Move
from renderer.mat4 import Mat4


def _magnitude(v):
    return math.sqrt(dot(v, v))
from renderer.mastermorphix_view import _VERTEX_SHADER,_FRAGMENT_SHADER,_VERTEX_FORMAT


PALETTE=((.98,.98,.98,1),(.02,.65,.18,1),(.9,.05,.06,1),(.51,.12,.73,1),
         (.97,.31,.61,1),(1,.47,.02,1),(.05,.2,.91,1),(.62,.86,.12,1),
         (1,.85,.02,1),(.02,.73,.83,1),(.58,.6,.64,1),(.2,.08,.47,1))
TETRA_PALETTE=((.91,.04,.04,1),(1,.85,0,1),(.06,.19,.9,1),(.01,.65,.18,1))
CUBE_PALETTE=((.98,.98,.98,1),(.9,.04,.05,1),(.01,.65,.18,1),
              (1,.85,0,1),(1,.46,.01,1),(.06,.19,.9,1))


def default_palette(cube):
    """Return the same factory face colors used when a model is first opened."""
    count=len(cube.geometry.spec.normals)
    return {4:TETRA_PALETTE,6:CUBE_PALETTE}.get(count,PALETTE)


def _inside(point,poly,normal):
    signs=[dot(cross(add(b,scale(a,-1)),add(point,scale(a,-1))),normal)
           for a,b in zip(poly,poly[1:]+poly[:1])]
    return min(signs)>=-1e-8 or max(signs)<=1e-8


def _outlines(sticker,normal):
    patches=sticker.patches or (sticker.polygon,)
    if len(patches)==1:
        return tuple(zip(patches[0],patches[0][1:]+patches[0][:1]))
    points=tuple(p for poly in patches for p in poly)
    result={}
    for poly in patches:
        for a,b in zip(poly,poly[1:]+poly[:1]):
            direction=add(b,scale(a,-1))
            length2=dot(direction,direction)
            if length2<1e-12:
                continue
            cuts={0.,1.}
            for p in points:
                delta=add(p,scale(a,-1))
                t=dot(delta,direction)/length2
                if 1e-7<t<1-1e-7 and dot(cross(delta,direction),cross(delta,direction))<1e-14:
                    cuts.add(t)
            cuts=sorted(cuts)
            perpendicular=scale(unit(cross(normal,direction)),1e-5)
            for lo,hi in zip(cuts,cuts[1:]):
                midpoint=add(a,scale(direction,(lo+hi)/2))
                left=any(_inside(add(midpoint,perpendicular),p,normal) for p in patches)
                right=any(_inside(add(midpoint,scale(perpendicular,-1)),p,normal) for p in patches)
                if left and right:
                    continue
                p,q=add(a,scale(direction,lo)),add(a,scale(direction,hi))
                result[tuple(sorted((key(p),key(q))))]=(p,q)
    return tuple(result.values())


@lru_cache(maxsize=3)
def outlines(kind,n):
    from cube.polyhedral import geometry
    g=geometry(kind,n)
    return tuple(_outlines(s,g.spec.normals[s.face]) for s in g.stickers)


class PolyhedralView(Widget):
    lock_rotation=BooleanProperty(True)
    yaw=NumericProperty(32)
    pitch=NumericProperty(22)
    roll=NumericProperty(0)
    observation_angle=NumericProperty(0)

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.cube=None
        self.palette=PALETTE
        self.selected=None
        self.on_pick=None
        self._polygons=[]
        self._fbo=None
        self._gpu_failed=False
        self._compatible=InstructionGroup()
        self.canvas.add(self._compatible)
        self._face_labels=[]
        self._event=None
        self._move=None
        self._fraction=0
        self._whole_world=Mat4()
        self._observation_axis=None
        self._observation_animation=None
        self._touch=None
        self._touch_start=None
        self._trigger=Clock.create_trigger(self._draw,0)
        self.bind(pos=self._trigger,size=self._trigger,yaw=self._trigger,pitch=self._trigger,roll=self._trigger)
        self.bind(observation_angle=self._trigger)

    @staticmethod
    def _depth_on(*args):
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

    @staticmethod
    def _depth_off(*args):
        glDisable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

    def _buffer(self):
        if self._gpu_failed:
            return False
        size=(max(1,int(self.width)),max(1,int(self.height)))
        if self._fbo is None:
            try:
                fbo=Fbo(size=size,with_depthbuffer=True,vs=_VERTEX_SHADER,fs=_FRAGMENT_SHADER)
                if not fbo.shader.success:
                    raise RuntimeError('Polyhedral shader compilation failed')
            except Exception:
                Logger.exception('Polyhedral: using compatible drawing')
                self._gpu_failed=True
                return False
            self._fbo=fbo
            with self._fbo:
                Callback(self._depth_on)
                ClearColor(0,0,0,0)
                ClearBuffers(clear_depth=True)
                self._group=InstructionGroup()
                Callback(self._depth_off)
            with self.canvas:
                Color(1,1,1,1)
                self._image=Rectangle(texture=self._fbo.texture)
            self._meshes=[]
            self.canvas.add(self._fbo)
            self.canvas.add(Color(1,1,1,1))
            # The offscreen buffer must execute before its display rectangle.
            self.canvas.remove(self._image)
            self.canvas.add(self._image)
        if self._fbo.size!=size:
            self._fbo.size=size
            self._image.texture=self._fbo.texture
        self._fbo['view_size']=(float(size[0]),float(size[1]))
        self._image.pos=self.pos
        self._image.size=self.size
        return True

    def set_cube(self,cube):
        self.cancel_animation()
        if self.cube is not cube:
            self._whole_world=Mat4()
            self.roll=0
        self.cube=cube
        count=len(cube.geometry.spec.normals)
        self.palette=default_palette(cube)
        if count==4:
            self.yaw=45
            self.pitch=math.degrees(math.atan(1/math.sqrt(2)))
        for label in self._face_labels:
            self.remove_widget(label)
        self._face_labels=[]
        for i in range(count):
            label=Label(text=str(i+1),size_hint=(None,None),size=(24,24),
                        font_size='13sp',bold=True,color=(1,1,1,1),
                        outline_width=1,outline_color=(.1,.12,.15,1))
            self.add_widget(label)
            self._face_labels.append(label)
        self._trigger()

    def refresh(self):
        self._trigger()

    def set_whole_world(self,world):
        self._whole_world=world
        self._trigger()

    def animate_whole_turn(self,axis,angle,duration,on_done=None):
        self.cancel_touch()
        self.cancel_observation()
        self._observation_axis=axis
        animation=Animation(observation_angle=angle,duration=duration,t='in_out_sine')
        self._observation_animation=animation
        def finish(*_):
            self._whole_world=Mat4.rotation_axis(angle,axis)*self._whole_world
            self._observation_axis=None
            self._observation_animation=None
            self.observation_angle=0
            if on_done:
                on_done()
            self.refresh()
        animation.bind(on_complete=finish)
        animation.start(self)

    def cancel_observation(self):
        if self._observation_animation is not None:
            self._observation_animation.cancel(self)
        self._observation_animation=None
        self._observation_axis=None
        self.observation_angle=0

    def observation_world(self):
        if self._observation_axis is None:
            return self._whole_world
        return Mat4.rotation_axis(self.observation_angle,self._observation_axis)*self._whole_world

    def reset_camera(self):
        Animation.cancel_all(self, 'yaw', 'pitch', 'roll')
        self.roll=0
        tetra = self.cube is not None and len(self.cube.geometry.spec.normals) == 4
        self.yaw = 45 if tetra else 32
        self.pitch = math.degrees(math.atan(1/math.sqrt(2))) if tetra else 22
        self.refresh()

    def turn_view(self,direction):
        Animation.cancel_all(self,'yaw')
        Animation(yaw=self.yaw+direction*72,duration=.45,t='in_out_sine').start(self)

    def animate_move(self,move,on_done=None,duration=.3):
        if self._move is not None or self.cube is None:
            return False
        self._move=move
        self._fraction=0
        elapsed=0
        interval=1/24 if len(self.cube.geometry.stickers)<600 else 1/12
        def tick(dt):
            nonlocal elapsed
            elapsed+=dt
            self._fraction=min(1.,elapsed/duration)
            self._draw()
            if self._fraction>=1:
                self.cube.apply_move(move)
                self._move=None
                self._event=None
                self._trigger()
                if on_done:
                    on_done()
                return False
        self._event=Clock.schedule_interval(tick,interval)
        return True

    def cancel_animation(self):
        self.cancel_observation()
        if self._event:
            self._event.cancel()
        self._event=None
        self._move=None
        Animation.cancel_all(self)

    def _draw(self,*args):
        if self.cube is None or self.width<2 or self.height<2:
            return
        gpu=self._buffer()
        g=self.cube.geometry
        yaw,pitch=math.radians(self.yaw),math.radians(self.pitch)
        eye=(math.sin(yaw)*math.cos(pitch),math.sin(pitch),math.cos(yaw)*math.cos(pitch))
        right=unit(cross((0,1,0),eye))
        up=cross(eye,right)
        if self.roll:
            angle=math.radians(self.roll)
            right,up=(add(scale(right,math.cos(angle)),scale(up,math.sin(angle))),
                      add(scale(up,math.cos(angle)),scale(right,-math.sin(angle))))
        radius=max(math.sqrt(dot(p,p)) for face in body(g.spec.normals) for p in face)
        factor=min(self.width,self.height)*.42/max(radius,1)
        cx,cy=self.width/2,self.height/2
        self._proj=(eye,right,up,factor,cx,cy)
        observation=self.observation_world()
        vertices=[]
        indices=[]
        chunks=[]
        compatible=[]
        self._polygons=[]
        boundaries=outlines(self.cube.puzzle_kind,self.cube.n)
        curved=self.cube.puzzle_kind=='moyu'
        if curved:
            from renderer.tower_mesh import tower_skin,tower_edge
            skin=tower_skin(self.cube.n)
        moving=set(g.layers[self._move.axis][self._move.layer]) if self._move else set()
        turn=None
        if self._move:
            amount=self._move.amount
            if amount>g.spec.turn_order/2:
                amount-=g.spec.turn_order
            angle=2*math.pi/g.spec.turn_order*amount*self._fraction
            turn=tuple(rotate(v,g.spec.axes[self._move.axis],angle)
                       for v in ((1,0,0),(0,1,0),(0,0,1)))
        def transform(p):
            if turn is None:
                return observation.transform(*p)
            x,y,z=p
            return observation.transform(turn[0][0]*x+turn[1][0]*y+turn[2][0]*z,
                                         turn[0][1]*x+turn[1][1]*y+turn[2][1]*z,
                                         turn[0][2]*x+turn[1][2]*y+turn[2][2]*z)
        def project(p):
            return (cx+dot(p,right)*factor,cy+dot(p,up)*factor,-dot(p,eye)*.12)
        def polygon(points,rgba,bias=0):
            if not gpu:
                compatible.append((tuple((x+self.x,y+self.y,z+bias) for x,y,z in points),rgba))
                return
            if len(vertices)//7+len(points)>60000:
                chunks.append((vertices[:],indices[:]))
                vertices.clear()
                indices.clear()
            base=len(vertices)//7
            for x,y,z in points:
                vertices.extend((x,y,z+bias,*rgba))
            for i in range(1,len(points)-1):
                indices.extend((base,base+i,base+i+1))
        def edge(a,b,rgba,width):
            dx,dy=b[0]-a[0],b[1]-a[1]
            length=math.hypot(dx,dy)
            if length<1e-6:
                return
            nx,ny=-dy/length*width,dx/length*width
            polygon(((a[0]+nx,a[1]+ny,a[2]),(a[0]-nx,a[1]-ny,a[2]),
                     (b[0]-nx,b[1]-ny,b[2]),(b[0]+nx,b[1]+ny,b[2])),rgba,-.0015)
        for i,s in enumerate(g.stickers):
            rotate_piece=s.piece in moving
            normal=transform(g.spec.normals[s.face]) if rotate_piece else observation.transform(*g.spec.normals[s.face])
            if not curved and dot(normal,eye)<=1e-8:
                continue
            color=self.cube.colors[i]
            rgba=self.palette[color] if color>=0 else (.37,.43,.5,1)
            patches=skin[i] if curved else tuple((patch,g.spec.normals[s.face])
                                                for patch in s.patches or (s.polygon,))
            visible=False
            for patch,patch_normal in patches:
                patch_normal=transform(patch_normal) if rotate_piece else observation.transform(*patch_normal)
                if dot(patch_normal,eye)<=1e-8:
                    continue
                visible=True
                brightness=.85+.15*max(0,dot(patch_normal,unit((-.3,.8,.52))))
                shade=tuple(c*brightness for c in rgba[:3])+(1,)
                world=tuple(transform(p) if rotate_piece else observation.transform(*p) for p in patch)
                pts=tuple(project(p) for p in world)
                polygon(pts,shade)
                self._polygons.append((pts,i))
            if not visible:
                continue
            for a,b in boundaries[i]:
                path=tower_edge(a,b,self.cube.n) if curved else (a,b)
                if rotate_piece:
                    path=tuple(transform(p) for p in path)
                else:
                    path=tuple(observation.transform(*p) for p in path)
                for a,b in zip(path,path[1:]):
                    edge(project(a),project(b),(.12,.16,.2,1),.6)
                    if i==self.selected:
                        edge(project(a),project(b),(.05,.84,1,1),1.5)
        if vertices:
            chunks.append((vertices,indices))
        for normal,label in zip(g.spec.normals,self._face_labels):
            normal=observation.transform(*normal)
            label.opacity=1 if self._move is None and dot(normal,eye)>.1 else 0
            x,y,_=project(normal)
            label.center=(self.x+x,self.y+y)
        if not gpu:
            if self._fbo is not None:
                self.canvas.remove(self._fbo)
                self.canvas.remove(self._image)
                self._fbo=None
            if not hasattr(self,'_fallback_texture'):
                self._fallback_texture=Texture.create(size=(1,1),colorfmt='rgba')
                def fill(texture):
                    texture.blit_buffer(bytes((255,255,255,255)),colorfmt='rgba',bufferfmt='ubyte')
                fill(self._fallback_texture)
                self._fallback_texture.add_reload_observer(fill)
            self._compatible.clear()
            for pts,rgba in sorted(compatible,key=lambda item:mean(item[0])[2],reverse=True):
                self._compatible.add(Color(*rgba))
                self._compatible.add(Mesh(vertices=[v for x,y,z in pts for v in (x,y,0.,0.)],
                    indices=list(range(len(pts))),mode='triangle_fan',texture=self._fallback_texture))
            return
        while len(self._meshes)<len(chunks):
            mesh=Mesh(vertices=[],indices=[],fmt=_VERTEX_FORMAT,mode='triangles')
            self._group.add(mesh)
            self._meshes.append(mesh)
        for i,mesh in enumerate(self._meshes):
            v,idx=chunks[i] if i<len(chunks) else ([],[])
            mesh.vertices=v
            mesh.indices=idx
        self._fbo.ask_update()

    def pick(self,x,y):
        hit=self.pick_surface(x,y)
        return hit[0] if hit is not None else None

    def pick_surface(self,x,y):
        x,y=x-self.x,y-self.y
        depth=float('inf')
        picked=None
        for polygon,index in self._polygons:
            a=polygon[0]
            for b,c in zip(polygon[1:],polygon[2:]):
                den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
                if abs(den)<1e-10:
                    continue
                u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
                v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den
                w=1-u-v
                if min(u,v,w)>=-1e-7:
                    z=u*a[2]+v*b[2]+w*c[2]
                    if z<depth:
                        depth,picked=z,index
        if picked is None:
            return None
        eye,right,up,factor,cx,cy=self._proj
        point=add(add(scale(right,(x-cx)/factor),scale(up,(y-cy)/factor)),
                  scale(eye,-depth/.12))
        return picked,point

    def cancel_touch(self):
        if self._touch is not None:
            self._touch.ungrab(self)
        self._touch=None
        self._touch_start=None

    def on_touch_down(self,touch):
        if self.collide_point(*touch.pos) and self._move is None and self._observation_animation is None:
            if self._touch is not None:
                return True
            self._touch=touch
            self._touch_start=touch.pos
            self._touch_last=touch.pos
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self,touch):
        if touch is self._touch:
            if not self.lock_rotation:
                self.yaw-=(touch.x-self._touch_last[0])*.4
                self.pitch=max(-80,min(80,self.pitch-(touch.y-self._touch_last[1])*.4))
                self._touch_last=touch.pos
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self,touch):
        if touch is self._touch:
            touch.ungrab(self)
            self._touch=None
            if sum((a-b)**2 for a,b in zip(touch.pos,self._touch_start))<100:
                index=self.pick(*touch.pos)
                if index is not None and self.on_pick:
                    self.on_pick(index)
            return True
        return super().on_touch_up(touch)


class PolyhedralTwistView(PolyhedralView):
    """Drag the actual contacted piece; orbit only when explicitly unlocked."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on_twist = None
        self.lock_view = True
        self.camera_busy = False
        self._grab = None

    def reset_camera(self):
        self.cancel_touch()
        Animation.cancel_all(self, 'yaw', 'pitch')
        self.camera_busy = False
        if self.cube and len(self.cube.geometry.spec.normals)==4:
            self.yaw=45
            self.pitch=math.degrees(math.atan(1/math.sqrt(2)))
        else:
            self.yaw=32
            self.pitch=22
        self.refresh()

    def cancel_touch(self):
        grab=self._grab
        self._grab=None
        if grab is not None:
            grab[0].ungrab(self)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if self._move is not None or self.camera_busy or self._grab is not None:
            return True
        if getattr(touch, 'is_mouse_scrolling', False):
            return True
        self._draw()
        index=self.pick(*touch.pos)
        if self.lock_view and index is None:
            return True
        self._grab=(touch,tuple(touch.pos),index,tuple(touch.pos),self.lock_view)
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if self._grab is None or touch is not self._grab[0]:
            return False
        pointer,start,index,last,locked=self._grab
        if not locked:
            self.yaw-=(touch.x-last[0])*.4
            self.pitch=max(-80,min(80,self.pitch-(touch.y-last[1])*.4))
            self._grab=(pointer,start,index,tuple(touch.pos),locked)
        return True

    def on_touch_up(self, touch):
        if self._grab is None or touch is not self._grab[0]:
            return False
        _,start,index,_,locked=self._grab
        self.cancel_touch()
        from ui.widgets import metrics as m
        drag=(touch.x-start[0],touch.y-start[1])
        if locked and math.hypot(*drag)>=m.h(18) and self.on_twist:
            move=self.resolve_twist(index,drag,start)
            if move is not None:
                self.on_twist(move)
        return True

    def resolve_twist(self, sticker_index, drag, press=None):
        from cube.polyhedral import Move
        from renderer.gesture import choose_turn
        proj=getattr(self,'_proj',None)
        if proj is None or self.cube is None or sticker_index is None:
            return None
        eye,right,up,factor,cx,cy=proj
        g=self.cube.geometry
        sticker=g.stickers[sticker_index]
        if press is None:
            point=mean(sticker.polygon)
        else:
            hit=self.pick_surface(*press)
            if hit is not None and hit[0]==sticker_index:
                point=hit[1]
            else:
                return None
        candidates=[]
        for axis,bands in enumerate(g.layers):
            for layer,band in enumerate(bands):
                if sticker.piece not in band:
                    continue
                velocity=cross(g.spec.axes[axis],point)
                candidates.append(((axis,layer),(dot(velocity,right),dot(velocity,up))))
                break
        chosen=choose_turn(drag,candidates)
        if chosen is None:
            return None
        (axis,layer),sign=chosen
        return Move(axis,layer,sign%g.spec.turn_order)
