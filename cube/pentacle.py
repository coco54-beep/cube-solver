"""Pentacle: freely rotating face discs and geometrically gated layers.

Five chords partition each disc. A core layer may only turn when none of
the physical panels straddle its cut plane. Disc turns are continuous.
"""
import math
from dataclasses import dataclass
from functools import lru_cache
from cube.polyhedral import CUBE,Spec,Geometry,Sticker,Move,add,scale,dot,cross,mean,clip,key,rotate,unit
from cube.appearance import IDENTITY_FRAME,transform_frame

RADIUS=.97
CUT=RADIUS*math.cos(math.tau/5)
EPS=1e-6
def multiplied(a,b):return tuple(tuple(round(x,12) for x in transform_frame(a,v)) for v in b)
def turned(axis,angle):return tuple(rotate(v,axis,math.radians(angle)) for v in IDENTITY_FRAME)

@dataclass(frozen=True)
class Panel:
    home:int
    face:int
    patches:tuple

@lru_cache(maxsize=1)
def shell():
    panels=[];homes={};discs=[]
    for face,normal in enumerate(CUBE):
        u=(1.,0.,0.) if not normal[0] else (0.,0.,1.)
        v=cross(normal,u)
        def point(x,y):return add(normal,add(scale(u,x),scale(v,y)))
        circle=tuple(point(RADIUS*math.cos(math.tau*i/60),RADIUS*math.sin(math.tau*i/60)) for i in range(60))
        regions=[circle]
        for j in range(5):
            angle=math.pi/2+j*math.tau/5
            axis=add(scale(u,math.cos(angle)),scale(v,math.sin(angle)))
            split=[]
            for polygon in regions:
                for n,b in ((axis,CUT),(scale(axis,-1),-CUT)):
                    part=clip(polygon,n,b)
                    if part:split.append(part)
            regions=split
        for polygon in regions:
            home=len(homes);homes[('disc',face,home)]=home
            panels.append(Panel(home,face,(polygon,)));discs.append(home)
        # Only the outer housing follows ordinary core cubies. Cut its ring
        # into the true core cells, keeping patches of one cubie together.
        groups={}
        for i,p in enumerate(circle):
            q=circle[(i+1)%60]
            def outer(a):
                d=add(a,scale(normal,-1));return add(normal,scale(d,1/max(abs(dot(d,u)),abs(dot(d,v)))))
            polygon=(outer(p),outer(q),q,p)
            cells=[((),polygon)]
            for axis in ((1,0,0),(0,1,0),(0,0,1)):
                split=[]
                for signature,part in cells:
                    for value,lo,hi in ((-1,-2.,-CUT),(0,-CUT,CUT),(1,CUT,2.)):
                        out=clip(clip(part,axis,hi),scale(axis,-1),-lo)
                        if out:split.append((signature+(value,),out))
                cells=split
            for signature,part in cells:groups.setdefault(signature,[]).append(part)
        for signature,patches in groups.items():
            home=homes.setdefault(('core',signature),len(homes))
            panels.append(Panel(home,face,tuple(patches)))
    return tuple(panels),len(homes),frozenset(discs)


class PentacleCube:
    puzzle_kind='pentacle'
    n=3
    rigid_family=True
    def __init__(self,frames=None,paints=None,history=()):
        self.panels,count,self.discs=shell()
        self.frames=tuple(frames) if frames is not None else (IDENTITY_FRAME,)*count
        self._paints=list(paints) if paints is not None else [p.face for p in self.panels]
        if len(self.frames)!=count or len(self._paints)!=len(self.panels):raise ValueError('rigid.invalid')
        self.history=list(history);self._history_snapshot=self.frames;self._geometry_cache=None;self._world_cache=None
    @classmethod
    def solved(cls):return cls()
    def clone(self):return type(self)(self.frames,self._paints,self.history if self.frames==self._history_snapshot else ())
    entered=clone
    @property
    def colors(self):
        # Generic playback checkpoints must carry BOTH the cut orientation
        # and the paint. This is deliberately not a sticker-colour array.
        return [(c,self.frames[p.home]) for c,p in zip(self._paints,self.panels)]
    @colors.setter
    def colors(self,values):
        if len(values)!=len(self.panels):raise ValueError('rigid.invalid')
        frames=list(self.frames);paints=[];seen={}
        for panel,(color,frame) in zip(self.panels,values):
            frame=tuple(tuple(row) for row in frame)
            if len(frame)!=3 or any(len(row)!=3 or not all(math.isfinite(x) for x in row) for row in frame):raise ValueError('rigid.invalid')
            if color not in range(-1,6) or panel.home in seen and seen[panel.home]!=frame:raise ValueError('rigid.invalid')
            seen[panel.home]=frame;frames[panel.home]=frame;paints.append(color)
        self.frames=tuple(frames);self._paints=paints;self.history=[];self._history_snapshot=self.frames;self._geometry_cache=None
    def paint(self,index,color):
        self._paints[index]=color;self.history=[]
    def world_panels(self):
        if self._world_cache is not None and self._world_cache[0]==self.frames:return self._world_cache[1]
        world=tuple(tuple(tuple(transform_frame(self.frames[p.home],v) for v in poly) for poly in p.patches) for p in self.panels)
        self._world_cache=(self.frames,world);return world
    def selection(self,axis,layer,strict=False):
        points={};normal=CUBE[axis];world=self.world_panels()
        for panel,patches in zip(self.panels,world):points.setdefault(panel.home,[]).extend(v for poly in patches for v in poly)
        selected=set()
        for home,vertices in points.items():
            projections=[dot(normal,v) for v in vertices];lo,hi=min(projections),max(projections)
            if layer==0:
                if home in self.discs and lo>1-EPS and hi<1+EPS:selected.add(home)
            elif lo>=CUT-EPS:selected.add(home)
            elif strict and hi>CUT+EPS:raise ValueError('pentacle.align_first')
        return frozenset(selected)
    @property
    def geometry(self):
        if self._geometry_cache is not None and self._geometry_cache[0]==self.frames:return self._geometry_cache[1]
        world=self.world_panels();stickers=[];pieces=[[] for _ in self.frames];points=[{} for _ in self.frames]
        for index,(panel,patches) in enumerate(zip(self.panels,world)):
            normal=transform_frame(self.frames[panel.home],CUBE[panel.face])
            face=max(range(6),key=lambda f:dot(CUBE[f],normal))
            stickers.append(Sticker(panel.home,face,patches[0],patches));pieces[panel.home].append(index)
            for poly in patches:
                for p in poly:points[panel.home][key(p)]=p
        layers=tuple((tuple(self.selection(a,0)),tuple(self.selection(a,1))) for a in range(6))
        g=Geometry(Spec('pentacle',3,CUBE,CUBE,(),360),tuple(stickers),tuple(tuple(p) for p in pieces),
                   tuple(mean(tuple(p.values())) for p in points),tuple(() for _ in CUBE),layers)
        self._geometry_cache=(self.frames,g);return g
    def step(self,axis,layer):return 1 if layer==0 else 90
    def moves(self):return tuple(Move(a,l,18 if l==0 else 90) for a in range(6) for l in (0,1))
    def proposed(self,move,guard=None):
        if guard:guard()
        if move.axis not in range(6) or move.layer not in (0,1) or not math.isfinite(move.amount):raise ValueError('rigid.invalid')
        if move.layer and abs(move.amount/90-round(move.amount/90))>EPS:raise ValueError('pentacle.align_first')
        chosen=self.selection(move.axis,move.layer,strict=True)
        frame=turned(CUBE[move.axis],move.amount)
        return tuple(multiplied(frame,f) if h in chosen else f for h,f in enumerate(self.frames))
    def can_apply(self,move):
        try:self.proposed(move);return True
        except ValueError:return False
    def apply_move(self,move,guard=None):
        frames=self.proposed(move,guard)
        if self.frames!=self._history_snapshot:self.history=[]
        self.frames=frames;self.history.append(move);self._history_snapshot=frames;self._geometry_cache=None
        return self
    def apply_moves(self,moves):
        for move in moves:self.apply_move(move)
        return self
    def alignment_moves(self,axis):
        """Nearest free disc adjustments that open this one core layer."""
        work=self.clone();result=[];target=CUBE[axis]
        for face,normal in enumerate(CUBE):
            if abs(dot(normal,target))>EPS:continue
            world=work.world_panels();candidates=[];disc=work.selection(face,0)
            for panel,patches in zip(work.panels,world):
                if panel.home not in disc:continue
                polygon=patches[0];centre=mean(polygon)
                distance=sum((a-b)**2 for a,b in zip(centre,normal))
                candidates.append((distance,polygon))
            if not candidates:raise ValueError('rigid.invalid')
            polygon=min(candidates,key=lambda c:c[0])[1];angles=[]
            for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                edge=add(b,scale(a,-1))
                if dot(edge,edge)<EPS*EPS:continue
                n=unit(cross(edge,normal));radial=add(mean((a,b)),scale(normal,-1))
                if dot(n,radial)<0:n=scale(n,-1)
                angle=math.degrees(math.atan2(dot(cross(n,target),normal),dot(n,target)))
                angles.append(angle)
            angle=min(angles,key=abs)
            if abs(angle)>EPS:
                move=Move(face,0,angle);work.apply_move(move);result.append(move)
        if not work.can_apply(Move(axis,1,90)):raise ValueError('pentacle.align_first')
        return tuple(result)
    def is_solved(self):
        faces=[set() for _ in CUBE]
        for p,color in zip(self.panels,self._paints):
            if color<0:return False
            normal=transform_frame(self.frames[p.home],CUBE[p.face])
            face=max(range(6),key=lambda f:dot(CUBE[f],normal))
            if dot(CUBE[face],normal)<1-EPS:return False
            faces[face].add(color)
        return all(len(f)==1 for f in faces) and len(set(next(iter(f)) for f in faces))==6
