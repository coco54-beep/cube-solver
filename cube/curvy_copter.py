"""Analytic sphere-cut kernel shared by research and the editable adapter.

Unlike a regular-slot Clover alias, the 44 coloured pieces retain their
rigid frames through partial turns. ALL interior material regions also
participate in cut clearance. These spherical cuts are a mathematical
reference, not yet verified against the manufacturer's conical cut and
internal tracks. The catalogue adapter declares its spherical profile explicitly.
"""
from functools import lru_cache
import math
from cube.polyhedral import CUBE,EDGE_AXES,Spec,Move,scale,dot,rotate,key,cross,unit
from cube.appearance import IDENTITY_FRAME,ROTATIONS,transform_frame
from cube.curved_partition import SphereCut,shell
from cube.spherical_cells import Plane,Arrangement

JUMBLE=math.degrees(math.acos(1/3))


@lru_cache(maxsize=1)
def cuts():
    # Sphere centres are on the edge rays. Radius 1.4 and the face-centre
    # incidence give 2*c*c-2*c+1=1.4**2, with the external root.
    c=(5+math.sqrt(73))/10
    return tuple(SphereCut(scale(axis,math.sqrt(2)*c),1.4) for axis in EDGE_AXES)


@lru_cache(maxsize=1)
def structure():
    polygons=shell(Spec('lanlan_curvy_copter',3,CUBE,EDGE_AXES,(),360),cuts())
    signatures=tuple(dict.fromkeys(mask for mask,face,polygon in polygons))
    if 0 in signatures:raise ValueError('Curvy Copter core unexpectedly has a coloured face')
    arrangement=Arrangement(tuple(Plane(n,1.) for n in CUBE),cuts())
    hidden=set(arrangement.positive_masks())-set(signatures)-{0}
    signatures+=tuple(sorted(hidden))+(0,)
    regions=tuple(arrangement.region(mask) for mask in signatures)
    owners={mask:i for i,mask in enumerate(signatures)}
    panels=tuple((owners[mask],face,polygon) for mask,face,polygon in polygons)
    return signatures,regions,panels


def frame_key(frame):return tuple(round(v,11) for column in frame for v in column)
def multiply(a,b):return tuple(transform_frame(a,column) for column in b)
def inverse_point(frame,p):return tuple(dot(column,p) for column in frame)


class CopterState:
    """Rigid poses for cut-clearance experiments, deliberately unpublished."""
    layout=staticmethod(structure)
    def __init__(self,frames=None,paints=None):
        self.signatures,self.regions,self.panels=self.layout()
        try:
            self.frames=(tuple(tuple(tuple(float(v) for v in column) for column in frame) for frame in frames)
                         if frames is not None else (IDENTITY_FRAME,)*len(self.regions))
        except (TypeError,ValueError,OverflowError):raise ValueError('rigid.invalid') from None
        try:self.paints=tuple(paints) if paints is not None else tuple(face for home,face,polygon in self.panels)
        except TypeError:raise ValueError('rigid.invalid') from None
        if len(self.frames)!=len(self.regions) or len(self.paints)!=len(self.panels):raise ValueError('rigid.invalid')
        for frame in self.frames:
            if (len(frame)!=3 or any(len(column)!=3 or not all(math.isfinite(v) for v in column) for column in frame)
                    or any(abs(dot(a,b)-(i==j))>1e-7 for i,a in enumerate(frame) for j,b in enumerate(frame))):
                raise ValueError('rigid.invalid')
            if dot(cross(frame[0],frame[1]),frame[2])<1-1e-7:raise ValueError('rigid.invalid')
        if any(type(c) is not int or c not in range(-1,6) for c in self.paints):raise ValueError('rigid.invalid')
    def clone(self):return type(self)(self.frames,self.paints)
    def signature(self):return tuple(frame_key(frame) for frame in self.frames),self.paints
    def observation_data(self):
        return dict(model='curvy-copter-sphere-reference',version=1,frames=self.frames,paints=self.paints)
    @classmethod
    def from_observation(cls,data):
        if (type(data) is not dict or data.get('model')!='curvy-copter-sphere-reference'
                or type(data.get('version')) is not int or data.get('version')!=1
                or type(data.get('frames')) not in (list,tuple)
                or type(data.get('paints')) not in (list,tuple)):
            raise ValueError('rigid.invalid')
        return cls(data['frames'],data['paints'])
    def selection(self,axis,guard=None):
        if type(axis) is not int or axis not in range(12):raise ValueError('rigid.invalid')
        target=cuts()[axis];selected=[]
        for home,(region,frame) in enumerate(zip(self.regions,self.frames)):
            if guard:guard()
            local=SphereCut(tuple(round(v,11) for v in inverse_point(frame,target.centre)),target.radius)
            side=region.side(local)
            if side==0:raise ValueError('rigid.blocked')
            if side>0:selected.append(home)
        if not selected:raise ValueError('rigid.blocked')
        return tuple(selected)
    def proposed(self,move,guard=None):
        if (type(move.layer) is not int or move.layer!=0 or type(move.amount) not in (int,float)
                or not math.isfinite(move.amount)):raise ValueError('rigid.invalid')
        selected=set(self.selection(move.axis,guard))
        angle=math.radians(move.amount)
        turn=tuple(rotate(column,EDGE_AXES[move.axis],angle) for column in IDENTITY_FRAME)
        return tuple(multiply(turn,frame) if home in selected else frame for home,frame in enumerate(self.frames))
    def apply_move(self,move,guard=None):
        # No state mutation takes place until every physical region clears.
        self.frames=self.proposed(move,guard)
        return self
    def can_apply(self,move):
        try:self.proposed(move);return True
        except ValueError:return False
    def moves(self):
        return tuple(Move(axis,0,angle) for axis in range(12)
                     for angle in (180.,JUMBLE,-JUMBLE,180.-JUMBLE,JUMBLE-180.))
    def world_panels(self):
        return tuple(tuple(transform_frame(self.frames[home],v) for v in polygon)
                     for home,face,polygon in self.panels)

    def aligned_permutation(self):
        """Identify slots by transformed cuts, without looking at colours."""
        indices={key(c.centre):i for i,c in enumerate(cuts())}
        owners={mask:i for i,mask in enumerate(self.signatures)}
        faces={key(n):i for i,n in enumerate(CUBE)}
        slots={(home,face):i for i,(home,face,polygon) in enumerate(self.panels)}
        pose_maps=[]
        for home,frame in enumerate(self.frames):
            proper=next((r for r in ROTATIONS if max(abs(a-b) for u,v in zip(frame,r) for a,b in zip(u,v))<1e-7),None)
            if proper is None:raise ValueError('copter.align_first')
            target=sum(1<<indices[key(transform_frame(proper,c.centre))]
                       for i,c in enumerate(cuts()) if self.signatures[home]&(1<<i))
            if target not in owners:raise ValueError('copter.invalid_shape')
            pose_maps.append((owners[target],tuple(faces[key(transform_frame(proper,n))] for n in CUBE)))
        if sorted(target for target,faces in pose_maps)!=list(range(len(self.regions))):
            raise ValueError('copter.invalid_shape')
        result=tuple(slots[(pose_maps[home][0],pose_maps[home][1][face])] for home,face,poly in self.panels)
        if sorted(result)!=list(range(len(result))):raise ValueError('copter.invalid_shape')
        return result

    def edge_phases(self):
        """Observed carrier phases; every carrier keeps its native edge ray."""
        result=[]
        for axis,normal in enumerate(EDGE_AXES):
            home=self.signatures.index(1<<axis);frame=self.frames[home]
            if sum((a-b)**2 for a,b in zip(transform_frame(frame,normal),normal))>1e-12:
                raise ValueError('copter.invalid_shape')
            seed=(0.,1.,0.) if abs(normal[1])<.9 else (1.,0.,0.)
            u=unit(cross(normal,seed));v=transform_frame(frame,u)
            result.append(math.degrees(math.atan2(dot(cross(u,v),normal),dot(u,v))))
        return tuple(result)
