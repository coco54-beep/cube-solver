"""Full-angle state for the explicitly labelled Twins geometric profile."""
import math
from functools import lru_cache
from cube.twins_material import structure,EDGE_CUT
from cube.crazy_comet import CometCube,vertices
from cube.lanlan_comet import polygon_key
from cube.appearance import IDENTITY_FRAME,transform_frame
from cube.curvy_copter import multiply,inverse_point,JUMBLE
from cube.polyhedral import EDGE_AXES,OCTA,CUBE,Move,Spec,Geometry,Sticker,dot,rotate,mean

AXES=EDGE_AXES+OCTA
SECOND=math.degrees(math.acos(1/math.sqrt(3)))


@lru_cache(maxsize=1)
def layout():
    solids,panels=structure();return tuple(range(len(solids))),solids,panels


@lru_cache(maxsize=8)
def _vertex_clouds(factory):
    # Avoid repeatedly hashing a complete curved mesh for every candidate cap.
    return tuple(vertices(solid) for solid in factory.layout()[1])


@lru_cache(maxsize=4096)
def _local_extent(factory,home,normal):
    # Exact floating-point key: rounding a normal would alter near-cut gates.
    values=tuple(dot(normal,p) for p in _vertex_clouds(factory)[home])
    return min(values),max(values)


class PlanarTwinsState(CometCube):
    puzzle_kind='mf8_twins'
    color_count=6
    layout=staticmethod(layout)
    turn_axes=AXES
    cut_bounds=(EDGE_CUT,)*12+(0.,)*8
    turn_steps=(180,)*12+(60,)*8
    observation_model='mf8-twins-material'

    def observation_data(self):
        return dict(model=self.observation_model,version=1,frames=self.frames,paints=self.paints)

    @classmethod
    def from_observation(cls,data):
        if (type(data) is not dict or data.get('model')!=cls.observation_model
                or type(data.get('version')) is not int or data.get('version')!=1
                or type(data.get('frames')) not in (list,tuple)
                or type(data.get('paints')) not in (list,tuple)):
            raise ValueError('rigid.invalid')
        return cls(data['frames'],data['paints'])

    @staticmethod
    def panel_normal(face,poly):return CUBE[face]

    def aligned_frames(self,home):
        from cube.rigid_placements import placements
        return tuple(frame for destination,frame,mapping in placements(type(self),home))

    def frame_aligned(self,home,frame):
        from cube.rigid_placements import frame_keys,pose_key
        return pose_key(frame) in frame_keys(type(self),home)

    def selection(self,axis,guard=None):
        if type(axis) is not int or axis not in range(len(self.turn_axes)):raise ValueError('rigid.invalid')
        bound=self.cut_bounds[axis];normal=self.turn_axes[axis];selected=[]
        for h,frame in enumerate(self.frames):
            if guard:guard()
            local=inverse_point(frame,normal);lo,hi=_local_extent(type(self),h,local)
            if lo>=bound-1e-8:selected.append(h)
            elif hi>bound+1e-8:raise ValueError('rigid.blocked')
        if not selected:raise ValueError('rigid.blocked')
        return tuple(selected)

    def proposed(self,move,guard=None):
        if (type(move.layer) is not int or move.layer!=0 or type(move.amount) not in (float,int)
                or not math.isfinite(move.amount)):raise ValueError('rigid.invalid')
        selected=set(self.selection(move.axis,guard))
        turn=tuple(rotate(p,self.turn_axes[move.axis],math.radians(move.amount)) for p in IDENTITY_FRAME)
        return tuple(multiply(turn,f) if h in selected else f for h,f in enumerate(self.frames))

    def moves(self):
        return tuple(Move(a,0,angle) for a in range(20) for angle in
                     ((180.,JUMBLE,-JUMBLE,SECOND,-SECOND,180-JUMBLE,JUMBLE-180,180-SECOND,SECOND-180)
                      if a<12 else (60.,-60.,120.,-120.,180.)))

    def aligned_permutation(self):
        slots={polygon_key(p):i for i,(h,c,p) in enumerate(self.panels)}
        result=[];owners={}
        for h,c,p in self.panels:
            target=slots.get(polygon_key(tuple(transform_frame(self.frames[h],v) for v in p)))
            if target is None:raise ValueError('copter.align_first')
            owner=self.panels[target][0]
            if h in owners and owners[h]!=owner:raise ValueError('copter.invalid_shape')
            owners[h]=owner;result.append(target)
        if sorted(result)!=list(range(len(self.panels))) or len(set(owners.values()))!=len(owners):
            raise ValueError('copter.invalid_shape')
        for h,target in owners.items():
            if polygon_key(tuple(transform_frame(self.frames[h],p) for p in vertices(self.solids[h])))!=polygon_key(vertices(self.solids[target])):
                raise ValueError('copter.invalid_shape')
        return tuple(result)

    @property
    def geometry(self):
        cached=getattr(self,'_geometry',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        panels=self.world_panels();pieces=[[] for _ in self.solids];stickers=[];layers=[]
        for i,((h,c,p),placed) in enumerate(zip(self.panels,panels)):
            normal=transform_frame(self.frames[h],CUBE[c]);face=max(range(6),key=lambda f:dot(CUBE[f],normal))
            stickers.append(Sticker(h,face,placed));pieces[h].append(i)
        for axis in range(len(self.turn_axes)):
            try:selected=self.selection(axis)
            except ValueError:selected=()
            layers.append((selected,))
        centres=tuple(transform_frame(f,mean(vertices(s))) for f,s in zip(self.frames,self.solids))
        g=Geometry(Spec(self.puzzle_kind,3,CUBE,self.turn_axes,(),360,axis_steps=self.turn_steps),
                   tuple(stickers),tuple(map(tuple,pieces)),centres,((),)*len(self.turn_axes),tuple(layers))
        self._geometry=self.frames,g;return g
