"""异形拍照的小预览，按真实色块轮廓绘制并播放整体翻面。"""
import numpy as np
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle, Triangle
from kivy.uix.widget import Widget
from renderer.mat4 import Mat4
from vision.scan_profiles import inside


class ScanSurfaceView(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.profile=None
        self.data={}
        self.world=Mat4()
        self.current_face=None
        self.on_cell=None
        self._animation=None
        self._event=None
        self._polygons=[]
        self._touch=None
        self._textures={}
        self.bind(pos=self._draw,size=self._draw)

    def set_scan(self,profile,data,world,face):
        self.profile,self.data,self.world,self.current_face=profile,data,world,face
        self._draw()

    def set_whole_world(self,world):
        self.world=world
        self._draw()

    def cancel_turn(self):
        if self._event:self._event.cancel()
        self._event=self._animation=None

    def animate_whole_turn(self,axis,angle,duration,on_done=None):
        self.cancel_turn()
        self._animation=[self.world,axis,angle,max(duration,.001),0.,on_done]
        self._event=Clock.schedule_interval(self._tick,0)

    def _tick(self,dt):
        if self._animation is None:return False
        base,axis,angle,duration,elapsed,done=self._animation
        elapsed+=max(0,dt)
        t=min(1.,elapsed/duration);eased=t*t*(3-2*t)
        self._animation[4]=elapsed
        self.world=Mat4.rotation_axis(angle*eased,axis)*base
        self._draw()
        if t>=1:
            self.cancel_turn()
            if done:done()
            return False
        return True

    def _draw(self,*_):
        self.canvas.clear();self._polygons=[]
        if self.profile is None or min(self.size)<2:return
        # 同一模型、同一相机始终使用固定缩放，翻面时不会改变大小。
        extent=max(np.linalg.norm(p) for poly in self.profile.body for p in poly)
        scale=min(self.size)*.38/max(extent*.82,.1)
        cx,cy=self.x+self.width/2,self.y+self.height/2
        camera_z=extent*6
        def project(points):
            points=np.array([self.world.transform(*p) for p in points])
            factor=camera_z/(camera_z-points[:,2])
            return np.column_stack((cx+points[:,0]*factor*scale,cy+points[:,1]*factor*scale)),points[:,2].mean()
        visible=[]
        for s in self.profile.surfaces:
            normal=self.world.transform(*self.profile.normals[s.face])
            center=self.world.transform(*np.mean(s.polygon,axis=0))
            if sum(n*(e-p) for n,e,p in zip(normal,(0,0,camera_z),center))<=1e-8:continue
            polygon,depth=project(s.polygon)
            visible.append((depth,s,polygon))
        visible.sort(key=lambda item:item[0])
        with self.canvas:
            for _,s,outline in visible:
                value=self.data.get(self.profile.face_keys[s.face],{}).get(s.index,-1)
                Color(*(self.profile.palette[value] if value>=0 else (.27,.32,.39,1)))
                for patch in s.patches:
                    points,_depth=project(patch)
                    for i in range(1,len(points)-1):
                        Triangle(points=[*points[0],*points[i],*points[i+1]])
                Color(.035,.045,.06,1)
                Line(points=outline.flatten().tolist(),close=True,width=1)
                self._polygons.append((outline,s.index,self.profile.face_keys[s.face]))
            for i,normal in enumerate(self.profile.normals):
                n=self.world.transform(*normal)
                center=np.mean(self.profile.body[i],axis=0)
                p=self.world.transform(*center)
                if sum(a*(b-c) for a,b,c in zip(n,(0,0,camera_z),p))<=0:continue
                point,_depth=project([center]);x,y=point[0]
                face=self.profile.face_keys[i]
                font=max(10,min(self.size)*.12)
                key=(face,round(font))
                if key not in self._textures:
                    label=CoreLabel(text=face,font_size=font,bold=True);label.refresh()
                    self._textures[key]=label.texture
                texture=self._textures[key];w,h=texture.size
                Color(.04,.05,.07,.85);Rectangle(pos=(x-w/2-1,y-h/2),size=(w+2,h))
                Color(1,1,1,1);Rectangle(texture=texture,pos=(x-w/2,y-h/2),size=texture.size)

    def on_touch_down(self,touch):
        if not self.collide_point(*touch.pos) or self._animation is not None:return False
        self._touch=touch.pos;touch.grab(self);return True

    def on_touch_move(self,touch):return touch.grab_current is self

    def on_touch_up(self,touch):
        if touch.grab_current is not self:return False
        touch.ungrab(self)
        start,self._touch=self._touch,None
        if start is None or self._animation is not None:return True
        if sum((a-b)**2 for a,b in zip(start,touch.pos))>16**2:return True
        for polygon,index,face in reversed(self._polygons):
            if inside(np.array([touch.pos]),polygon)[0]:
                if face==self.current_face and self.on_cell:self.on_cell(index,None)
                break
        return True
