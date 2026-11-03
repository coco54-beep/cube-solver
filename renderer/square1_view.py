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
from renderer.entry_style import UNENTERED,PLASTIC,SEAM,SELECTION,shade_unentered,stroke

OUTER_HEIGHT=1.
MIDDLE_HEIGHT=1/3


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


def entry_groups(cube):
    """Unknown slots remain visible/selectable without inventing identities."""
    groups=list(cube.groups())
    if getattr(cube,'color_entry',False) and getattr(cube,'show_entry_scaffold',True):
        groups.extend((slot//12,slot%12,1,None) for slot,piece in enumerate(cube.slots) if piece<0)
    return groups


def empty_ring(layer,start,layers=2):
    direction=1 if layer<layers/2 else -1
    points=[(0.,0.)]
    for offset in (0,1):
        angle=math.radians(-15+direction*(start+offset)*30)
        radius=1/max(abs(math.sin(angle)),abs(math.cos(angle)))
        points.append((radius*math.sin(angle),radius*math.cos(angle)))
    return tuple(points)


@lru_cache(maxsize=16)
def _piece_colors(piece):
    return piece_colors(piece)


def surfaces(cube):
    result=[]
    for layer,start,width,piece in entry_groups(cube):
        outline=empty_ring(layer,start) if piece is None else _ring(layer,start,width)
        # Adjacent closed layers meet; their visible gap is the shared stroke.
        low,high=(MIDDLE_HEIGHT,OUTER_HEIGHT) if layer==0 else (-OUTER_HEIGHT,-MIDDLE_HEIGHT)
        bottom=tuple((x,low,z) for x,z in outline)
        top=tuple((x,high,z) for x,z in outline)
        cap,sides=((-2,(-2,)) if piece is None else
                   cube.piece_colors(piece) if getattr(cube,'color_entry',False) else _piece_colors(piece))
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
        h=MIDDLE_HEIGHT
        box=[(x,y,z) for x,y,z in ((-1.,-h,-1.),(1.,-h,-1.),(1.,h,-1.),(-1.,h,-1.),
                                  (-1.,-h,1.),(1.,-h,1.),(1.,h,1.),(-1.,h,1.))]
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
    pick_black_surfaces=False
    _surfaces=staticmethod(surfaces)

    def _physical_outlines(self):
        """Optional full-panel outlines for tessellated physical surfaces."""
        return None

    def _surface_shade(self, normal, eye, light, rgba, color, recorded):
        brightness=.82+.18*max(0,dot(normal,light))
        return tuple(v*brightness for v in rgba[:3])+(1,)

    def _surface_depth_bias(self,color):
        return 0.

    def _display_surfaces(self,cube):
        return self._surfaces(cube)

    def _inset(self,points):
        return points

    def _is_recorded(self,slot):
        return self.recorded is None or slot>=24 or self.cube.slots[slot] in self.recorded

    def _is_selected(self,slot):
        return slot==self.selected

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
        faces=self._display_surfaces(self.cube)
        observation=self.observation_world()
        if not self.show_middle:
            faces=tuple(s for s in faces if s[4]<getattr(self.cube,'layer_count',2))
        if self.fit_piece and faces:
            points=[observation.transform(*p) for surface in faces for p in surface[0]]
            xs,ys=[dot(p,right) for p in points],[dot(p,up) for p in points]
            factor=min(self.width,self.height)*.82/max(max(xs)-min(xs),max(ys)-min(ys),.01)
            cx-=(max(xs)+min(xs))/2*factor
            cy-=(max(ys)+min(ys))/2*factor
        self._proj=(eye,right,up,factor,cx,cy)
        if not self.fit_piece:
            target=observation.transform(*self.camera_target)
            cx-=dot(target,right)*factor
            cy-=dot(target,up)*factor
            self._proj=(eye,right,up,factor,cx,cy)
        vertices,indices,compatible=[],[],[]
        self._polygons=[]
        entry_edges={}
        physical_outlines=self._physical_outlines()
        outlined_slots=set()
        light=unit((-.3,.8,.52))
        for points,normal,color,slot,layer,start,width in faces:
            original_normal=normal
            points,normal=self._motion(points,normal,slot,layer,start,width)
            points=tuple(observation.transform(*p) for p in points)
            normal=observation.transform(*normal)
            if dot(normal,eye)<=1e-8:
                continue
            unentered=color==-2 or color>=0 and not self._is_recorded(slot)
            rgba=UNENTERED if unentered else self.palette[color] if color>=0 else PLASTIC
            if not unentered:points=self._inset(points)
            shade=self._surface_shade(normal,eye,light,rgba,color,color<0 or self._is_recorded(slot))
            if unentered:shade=shade_unentered(normal)
            if self._is_selected(slot) and not unentered:
                shade=tuple(.75*v+.25*c for v,c in zip(shade,(0.,.9,1.,1.)))
            depth_bias=self._surface_depth_bias(color)
            projected=tuple((cx+dot(p,right)*factor,cy+dot(p,up)*factor,-dot(p,eye)*.12+depth_bias) for p in points)
            if color>=0 or color==-2:
                edges=zip(projected,projected[1:]+projected[:1])
                if physical_outlines is not None:
                    edges=[]
                    if slot not in outlined_slots:
                        outlined_slots.add(slot)
                        for a,b in physical_outlines.get(slot,()):
                            endpoints,_=self._motion((a,b),original_normal,slot,layer,start,width)
                            edge=[]
                            for p in endpoints:
                                p=observation.transform(*p)
                                edge.append((cx+dot(p,right)*factor,cy+dot(p,up)*factor,-dot(p,eye)*.12+depth_bias))
                            edges.append(edge)
                for a,b in edges:
                    edge_key=tuple(sorted((tuple(round(v,5) for v in a),tuple(round(v,5) for v in b))))
                    selected=self._is_selected(slot) or entry_edges.get(edge_key,(None,None,False))[2]
                    entry_edges[edge_key]=(a,b,selected)
            if color>=0 or color==-2 or self.pick_black_surfaces:
                self._polygons.append((projected,slot))
            base=len(vertices)//7
            for x,y,z in projected:
                vertices.extend((x,y,z,*shade))
            for i in range(1,len(projected)-1):
                indices.extend((base,base+i,base+i+1))
            compatible.append((projected,shade))
        # The same screen-space strokes frame grey and coloured panels.
        for a,b,selected in entry_edges.values():
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            if length<1e-6:continue
            half=stroke('selection' if selected else 'seam');nx,ny=-dy/length*half,dx/length*half
            rgba=SELECTION if selected else SEAM
            quad=((a[0]+nx,a[1]+ny,a[2]-.0015),(a[0]-nx,a[1]-ny,a[2]-.0015),
                  (b[0]-nx,b[1]-ny,b[2]-.0015),(b[0]+nx,b[1]+ny,b[2]-.0015))
            base=len(vertices)//7
            for x,y,z in quad:vertices.extend((x,y,z,*rgba))
            indices.extend((base,base+1,base+2,base,base+2,base+3))
            compatible.append((quad,rgba))
        if self._buffer():
            from renderer.mesh_batches import triangle_batches
            used=0
            for used,(batch_vertices,batch_indices) in enumerate(triangle_batches(vertices,indices),1):
                if len(self._meshes)<used:
                    mesh=Mesh(vertices=[],indices=[],fmt=_VERTEX_FORMAT,mode='triangles')
                    self._group.add(mesh);self._meshes.append(mesh)
                mesh=self._meshes[used-1]
                mesh.indices=[];mesh.vertices=batch_vertices;mesh.indices=batch_indices
            # A later view or smaller pose must not retain old batches on screen.
            for mesh in self._meshes[used:]:
                mesh.indices=[];mesh.vertices=[]
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
