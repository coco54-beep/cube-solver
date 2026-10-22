"""Rigid, state-dependent Mixup and Tangram mechanisms.

Moves rotate whole solids. Pose, piece identity and original coloured panels
remain attached; no colour-only projection is used as a replacement state.
"""
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from types import MappingProxyType
import math
from cube.polyhedral import CUBE,Spec,Geometry,Sticker,Move,body,unit,dot,cross,mean,rotate,scale,key
from cube.appearance import ROTATIONS,IDENTITY_FRAME,transform_frame
from cube.mirror_tower import _clip_solid

MIXUP_MODELS={
 'mixup_333':((3,3,3),False),'mixup_334':((3,4,3),False),
 'mixup_344':((3,4,4),False),'mixup_444':((4,4,4),False),
 'mixup_plus_333':((3,3,3),True),'mixup_plus_334':((3,4,3),True),
 'mixup_plus_344':((3,4,4),True),'mixup_plus_444':((4,4,4),True),
}
TANGRAM_MODELS=('tangram','tangram_extreme')
KINDS=tuple(MIXUP_MODELS)+TANGRAM_MODELS
EPS=1e-7


def multiply(a,b):return tuple(transform_frame(a,v) for v in b)
def frame_key(f):return tuple(round(v,8) for row in f for v in row)
def turn_frame(axis,angle):return tuple(rotate(v,axis,angle) for v in IDENTITY_FRAME)


@lru_cache(maxsize=3)
def poses(family):
    found={frame_key(IDENTITY_FRAME):IDENTITY_FRAME}
    if family=='mixup':
        x=turn_frame((1,0,0),math.pi/4);y=turn_frame((0,1,0),math.pi/4)
        for a in ROTATIONS:
            for b in ROTATIONS:
                for middle in (IDENTITY_FRAME,x,multiply(x,y)):
                    frame=multiply(a,multiply(middle,b));found.setdefault(frame_key(frame),frame)
    else:
        axis=unit((1,1,1));side=unit((1,-1,0));steps=12 if family=='tangram_extreme' else 6
        for i in range(steps//2):
            a=turn_frame(axis,i*math.tau/(steps//2))
            for b in (IDENTITY_FRAME,turn_frame(side,math.pi)):
                frame=multiply(a,b);found.setdefault(frame_key(frame),frame)
    return tuple(found.values())


@lru_cache(maxsize=3)
def pose_index(family):
    # Search branches share this immutable catalogue instead of rebuilding
    # its dictionary on every clone.
    return MappingProxyType({frame_key(f):i for i,f in enumerate(poses(family))})


@lru_cache(maxsize=3)
def proper_poses(family):
    proper=frozenset(frame_key(f) for f in ROTATIONS)
    return frozenset(i for i,f in enumerate(poses(family)) if frame_key(f) in proper)


@dataclass(frozen=True)
class Solid:
    faces:tuple
    anchor:tuple
    role:str


def clipped(polygons,normal,bound):
    return tuple(_clip_solid(list(polygons),normal,bound))


def box(bounds):
    polys=tuple((p,i) for i,p in enumerate(body(CUBE)))
    for axis,(low,high) in enumerate(bounds):
        normal=tuple(float(a==axis) for a in range(3))
        if high<1-EPS:polys=clipped(polys,normal,high)
        if low>-1+EPS:polys=clipped(polys,scale(normal,-1),-low)
    return polys


def vertices(faces):return tuple({key(p):p for poly,color in faces for p in poly}.values())


@lru_cache(maxsize=10)
def solids(kind):
    if kind in MIXUP_MODELS:
        dimensions,plus=MIXUP_MODELS[kind]
        depth=(2*math.sqrt(2)-1)/7 if plus else math.sqrt(2)-1
        long=(1-depth)/2
        cuts=[(-1,-depth,0,depth,1) if n==4 else (-1,-depth,depth,1) for n in dimensions]
        result=[]
        for indices in product(*(range(len(c)-1) for c in cuts)):
            outer=[a for a,i in enumerate(indices) if i in (0,len(cuts[a])-2)]
            if not outer:continue
            bounds=tuple((cuts[a][i],cuts[a][i+1]) for a,i in enumerate(indices))
            original=box(bounds);anchor=tuple((a+b)/2 for a,b in bounds)
            if not plus or len(outer)!=2:
                result.append(Solid(original,anchor,('centre','edge','corner')[len(outer)-1]));continue
            a,b=outer;sa=1 if anchor[a]>0 else -1;sb=1 if anchor[b]>0 else -1
            difference=tuple(sa if i==a else -sb if i==b else 0 for i in range(3))
            total=tuple(sa if i==a else sb if i==b else 0 for i in range(3))
            large=clipped(clipped(original,difference,long),scale(difference,-1),long)
            large=clipped(large,scale(total,-1),-(2*depth+long))
            edge_anchor=list(anchor);edge_anchor[a]=sa*(depth+1.5*long);edge_anchor[b]=sb*(depth+1.5*long)
            result.append(Solid(large,tuple(edge_anchor),'edge'))
            for first,second,sign in ((a,b,1),(b,a,-1)):
                small=clipped(original,scale(difference,-sign),-long)
                point=list(anchor);point[first]=1 if anchor[first]>0 else -1
                point[second]=(depth+long/2)*(1 if anchor[second]>0 else -1)
                result.append(Solid(small,tuple(point),'inner_edge'))
        return tuple(result)
    if kind not in TANGRAM_MODELS:raise ValueError('Unsupported articulated puzzle')
    principal=unit((1,1,1));sides=tuple(unit(v) for v in ((1,-1,0),(0,1,-1),(-1,0,1)))
    shell=tuple((p,i) for i,p in enumerate(body(CUBE)));result=[]
    for band in range(3):
        part=shell
        if band<2:part=clipped(part,principal,(-1 if band==0 else 1)/math.sqrt(3))
        if band>0:part=clipped(part,scale(principal,-1),-(1 if band==2 else -1)/math.sqrt(3))
        pieces=[part]
        planes=[(axis,.5/math.sqrt(2)) for axis in sides]
        if kind=='tangram_extreme' and band!=1:planes += [(scale(axis,-1),.5/math.sqrt(2)) for axis in sides]
        for normal,bound in planes:
            split=[]
            for polys in pieces:
                projections=[dot(normal,p) for p in vertices(polys)]
                if min(projections)<bound-EPS and max(projections)>bound+EPS:
                    split.extend((clipped(polys,normal,bound),clipped(polys,scale(normal,-1),-bound)))
                else:split.append(polys)
            pieces=split
        for polys in pieces:
            if not any(color>=0 for p,color in polys):continue
            points=vertices(polys)
            result.append(Solid(tuple(polys),mean(points),'band' if band==1 else 'cap'))
    return tuple(result)


def _box(points):return tuple((min(p[a] for p in points),max(p[a] for p in points)) for a in range(3))


def overlap(left,right):
    """Positive-volume convex intersection; touching boundaries are allowed."""
    lv,rv=vertices(left),vertices(right);lb,rb=_box(lv),_box(rv)
    if any(a[1]<=b[0]+EPS or b[1]<=a[0]+EPS for a,b in zip(lb,rb)):return False
    normals=[];edges=[[],[]]
    for side,faces in enumerate((left,right)):
        for points,color in faces:
            if len(points)<3:continue
            normal=cross(tuple(points[1][a]-points[0][a] for a in range(3)),tuple(points[2][a]-points[0][a] for a in range(3)))
            if dot(normal,normal)>EPS*EPS:normals.append(unit(normal))
            for a,b in zip(points,points[1:]+points[:1]):
                delta=tuple(b[i]-a[i] for i in range(3))
                if dot(delta,delta)>EPS*EPS:edges[side].append(unit(delta))
    normals.extend(cross(a,b) for a in edges[0] for b in edges[1])
    for normal in normals:
        if dot(normal,normal)<EPS*EPS:continue
        l=[dot(normal,p) for p in lv];r=[dot(normal,p) for p in rv]
        if max(l)<=min(r)+EPS or max(r)<=min(l)+EPS:return False
    return True


class ArticulatedCube:
    rigid_family=True
    def __init__(self,kind='mixup_333',frames=None,history=()):
        if kind not in KINDS:raise ValueError('Unsupported articulated puzzle')
        self.puzzle_kind=kind;self.n=max(MIXUP_MODELS[kind][0]) if kind in MIXUP_MODELS else 3
        self.solids=solids(kind);self.family='mixup' if kind in MIXUP_MODELS else kind
        self.orientations=poses(self.family);self._pose_index=pose_index(self.family)
        self.frames=tuple(frames) if frames is not None else (0,)*len(self.solids)
        if len(self.frames)!=len(self.solids) or any(type(i) is not int or not 0<=i<len(self.orientations) for i in self.frames):
            raise ValueError('rigid.invalid')
        self.history=list(history);self._history_snapshot=self.frames;self._geometry_cache=None
    @classmethod
    def solved(cls,kind='mixup_333'):return cls(kind)
    def clone(self):
        result=type(self)(self.puzzle_kind,self.frames,self.history if self.frames==self._history_snapshot else ())
        # Geometry is immutable and keyed by frames. Applying a move drops
        # only this clone's reference, leaving the source untouched.
        result._geometry_cache=self._geometry_cache
        return result
    entered=clone
    @property
    def colors(self):return list(self.frames)
    @colors.setter
    def colors(self,value):
        value=tuple(value)
        if len(value)!=len(self.solids) or any(type(i) is not int or not 0<=i<len(self.orientations) for i in value):raise ValueError('rigid.invalid')
        self.frames=value;self.history=[];self._history_snapshot=value;self._geometry_cache=None
    def placed_faces(self,home,pose=None):
        frame=self.orientations[self.frames[home] if pose is None else pose]
        return tuple((tuple(transform_frame(frame,p) for p in points),color) for points,color in self.solids[home].faces)
    def _bands(self):
        if self.family=='mixup':
            dimensions,plus=MIXUP_MODELS[self.puzzle_kind];depth=(2*math.sqrt(2)-1)/7 if plus else math.sqrt(2)-1
            axes=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
            cuts=tuple((-depth,0.,depth) if n==4 else (-depth,depth) for n in dimensions)
        else:
            axes=tuple(unit(v) for v in ((1,-1,0),(0,1,-1),(-1,0,1),(1,1,1)))
            cuts=((.5/math.sqrt(2),),)*3+((-1/math.sqrt(3),1/math.sqrt(3)),)
        return axes,cuts
    @property
    def geometry(self):
        if self._geometry_cache is not None and self._geometry_cache[0]==self.frames:return self._geometry_cache[1]
        axes,cuts=self._bands();period=8 if self.family=='mixup' else 6
        spec=Spec(self.puzzle_kind,self.n,CUBE,axes,(),period)
        centres=tuple(transform_frame(self.orientations[pose],solid.anchor) for solid,pose in zip(self.solids,self.frames))
        layers=[]
        for axis,bounds in zip(axes,cuts):
            bins=[[] for _ in range(len(bounds)+1)]
            for home,centre in enumerate(centres):bins[sum(dot(axis,centre)>b+EPS for b in bounds)].append(home)
            if self.family!='mixup' and len(bounds)==1:bins=bins[1:]
            layers.append(tuple(tuple(b) for b in bins))
        stickers=[];pieces=[]
        for home,solid in enumerate(self.solids):
            slots=[]
            for points,color in solid.faces:
                if color>=0:slots.append(len(stickers));stickers.append(Sticker(home,color,points))
            pieces.append(tuple(slots))
        g=Geometry(spec,tuple(stickers),tuple(pieces),centres,tuple(() for a in axes),tuple(layers))
        self._geometry_cache=(self.frames,g);return g
    def step(self,axis,layer):
        if self.family=='mixup':return 2 if layer in (0,len(self.geometry.layers[axis])-1) else 1
        return 3 if axis<3 else 1 if self.family=='tangram_extreme' and layer in (0,2) else 2
    def moves(self):
        return tuple(Move(a,l,self.step(a,l)) for a,bands in enumerate(self.geometry.layers) for l,band in enumerate(bands) if band)
    def proposed(self,move,collisions=True,guard=None):
        if guard:guard()
        g=self.geometry
        if not 0<=move.axis<len(g.layers) or not 0<=move.layer<len(g.layers[move.axis]):raise ValueError('rigid.blocked')
        if move.amount%self.step(move.axis,move.layer):raise ValueError('rigid.blocked')
        selected=set(g.layers[move.axis][move.layer]);axis=g.spec.axes[move.axis]
        if not selected:raise ValueError('rigid.blocked')
        if self.family=='mixup':
            from cube.mixup import check_slice_clearance
            check_slice_clearance(self,move,selected,guard)
        else:
            axes,cuts=self._bands()
            boundaries=cuts[move.axis]
            if move.axis==3:
                boundaries=boundaries[max(0,move.layer-1):min(len(boundaries),move.layer+1)]
            for home in range(len(self.solids)):
                projections=[dot(axis,p) for p in vertices(self.placed_faces(home))]
                if any(min(projections)<b-EPS and max(projections)>b+EPS for b in boundaries):raise ValueError('rigid.blocked')
        turn=turn_frame(axis,math.tau*move.amount/g.spec.turn_order);frames=list(self.frames)
        for home in selected:
            pose=self._pose_index.get(frame_key(multiply(turn,self.orientations[frames[home]])))
            if pose is None or not self.pose_allowed(home,pose):raise ValueError('rigid.blocked')
            frames[home]=pose
        if collisions and self.family!='mixup':
            # Mixup's mandatory slab-clearance check already separates every
            # moving panel from every stationary panel along this axis.
            # Rotation preserves that coordinate throughout the move, so a
            # quadratic endpoint panel check would repeat the same constraint.
            # Tangram still requires its full solid-volume intersection check.
            intersects=overlap
            stationary=[(h,self.placed_faces(h)) for h in range(len(self.solids)) if h not in selected]
            for home in selected:
                if guard:guard()
                moved=self.placed_faces(home,frames[home])
                if any(intersects(moved,faces) for h,faces in stationary):raise ValueError('rigid.blocked')
        return tuple(frames)
    def can_apply(self,move):
        try:self.proposed(move);return True
        except ValueError:return False
    def apply_move(self,move,guard=None):
        frames=self.proposed(move,guard=guard)
        if self.frames!=self._history_snapshot:self.history=[]
        self.frames=frames;self.history.append(move);self._history_snapshot=frames;self._geometry_cache=None
        return self
    def apply_moves(self,moves):
        for move in moves:self.apply_move(move)
        return self
    def is_solved(self):
        if not any(self.frames):return True
        # A solved assembly has one shared frame, apart from rotations of
        # panels that are geometrically indistinguishable. Reject broken
        # face normals cheaply before comparing complete panel outlines.
        for home,pose in enumerate(self.frames):
            for points,color in self.solids[home].faces:
                if color<0:continue
                normal=transform_frame(self.orientations[pose],CUBE[color])
                if not any(dot(normal,n)>1-EPS for n in CUBE):return False
        def signature(frame_ids):
            return tuple(sorted((color,tuple(sorted(key(transform_frame(self.orientations[pose],p)) for p in points)))
                                for solid,pose in zip(self.solids,frame_ids) for points,color in solid.faces if color>=0))
        actual=signature(self.frames)
        proper={frame_key(f) for f in ROTATIONS}
        return any(actual==signature((i,)*len(self.solids)) for i,frame in enumerate(self.orientations) if frame_key(frame) in proper)
    def pose_allowed(self,home,pose):
        return not (self.family=='mixup' and self.solids[home].role=='corner') or pose in proper_poses(self.family)
    def record_pose(self,home,pose,recorded):
        if not 0<=home<len(self.solids) or not 0<=pose<len(self.orientations) or not self.pose_allowed(home,pose):raise ValueError('rigid.invalid')
        faces=self.placed_faces(home,pose)
        if self.family=='mixup':
            from cube.mixup import skins_cross
            intersects=skins_cross
        else:intersects=overlap
        if any(intersects(faces,self.placed_faces(other)) for other in recorded if other!=home):raise ValueError('rigid.overlap')
        frames=list(self.frames);frames[home]=pose;self.frames=tuple(frames)
        self.history=[];self._history_snapshot=self.frames;self._geometry_cache=None
