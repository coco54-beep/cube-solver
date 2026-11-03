"""DWG curved solids with whole-material guarded shape-changing turns."""
import math
from functools import lru_cache
from cube.polyhedral import CUBE,Move,Spec,Geometry,Sticker,mean,key,rotate
from cube.appearance import IDENTITY_FRAME,ROTATIONS,transform_frame
from cube.curvy_copter import multiply,JUMBLE
from cube.copter_input import CopterCube
from cube.flower_material import AXES,structure,cuts


def frame_action(frame):
    proper=tuple(tuple(round(v) for v in col) for col in frame)
    if (proper not in ROTATIONS or any(abs(a-b)>=1e-7 for u,v in zip(frame,proper) for a,b in zip(u,v))):
        raise ValueError('flower.regular_only')
    return canonical_frame_action(proper)


@lru_cache(maxsize=24)
def canonical_frame_action(proper):
    axes={key(n):i for i,n in enumerate(AXES)};faces={key(n):i for i,n in enumerate(CUBE)}
    return (tuple(axes[key(transform_frame(proper,n))] for n in AXES),
            tuple(faces[key(transform_frame(proper,n))] for n in CUBE))


@lru_cache(maxsize=5000)
def transform_mask(mask,permutation):return sum(1<<permutation[i] for i in range(20) if mask&(1<<i))


class FlowerCopterCube(CopterCube):
    puzzle_kind='lanlan_flower_copter'
    geometry_profile='dwg-spheres-jumbling'
    observation_model='lanlan-flower-copter-dwg-spheres-regular-v1'
    layout=staticmethod(structure)
    turn_axes=AXES
    turn_steps=(180,)*12+(60,)*8

    def observation_data(self):
        return dict(model=self.observation_model,version=1,frames=self.frames,paints=self.paints)

    @classmethod
    def from_observation(cls,data):
        if (type(data) is not dict or data.get('model')!=cls.observation_model
                or type(data.get('version')) is not int or data.get('version')!=1
                or type(data.get('frames')) not in (list,tuple)
                or type(data.get('paints')) not in (list,tuple)):raise ValueError('rigid.invalid')
        return cls(data['frames'],data['paints'])

    def _pose_maps(self):
        cached=getattr(self,'_cached_pose_maps',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        owners={m:i for i,m in enumerate(self.signatures)};result=[]
        for mask,frame in zip(self.signatures,self.frames):
            axes,faces=frame_action(frame);target=transform_mask(mask,axes)
            if target not in owners:raise ValueError('copter.invalid_shape')
            result.append((owners[target],faces,target))
        if sorted(h for h,f,m in result)!=list(range(len(self.regions))):raise ValueError('copter.invalid_shape')
        result=tuple(result);self._cached_pose_maps=self.frames,result;return result

    def validate_pose(self):
        try:self._pose_maps()
        except ValueError as exc:
            if str(exc) not in ('flower.regular_only','twins.regular_only'):raise

    def aligned_frames(self,home):return ROTATIONS

    def frame_aligned(self,home,frame):
        proper=tuple(tuple(round(v) for v in col) for col in frame)
        return proper in ROTATIONS and max(abs(a-b) for u,v in zip(frame,proper) for a,b in zip(u,v))<1e-7

    def shape_weights(self):return (1,)*len(self.frames)

    def aligned_permutation(self):
        try:poses=self._pose_maps()
        except ValueError as exc:
            if str(exc) in ('flower.regular_only','twins.regular_only'):raise ValueError('copter.align_first') from None
            raise
        slots={(h,f):i for i,(h,f,p) in enumerate(self.panels)}
        try:result=tuple(slots[poses[h][0],poses[h][1][f]] for h,f,p in self.panels)
        except KeyError:raise ValueError('copter.invalid_shape') from None
        if sorted(result)!=list(range(len(result))):raise ValueError('copter.invalid_shape')
        return result

    def selection(self,axis,guard=None):
        if type(axis) is not int or axis not in range(20):raise ValueError('rigid.invalid')
        try:poses=self._pose_maps()
        except ValueError as exc:
            if str(exc) not in ('flower.regular_only','twins.regular_only','copter.align_first'):raise
            return self.material_selection(axis,guard)
        selected=[]
        for h,(target,faces,mask) in enumerate(poses):
            if guard:guard()
            # Each whole Boolean cell is entirely on its signed side of this
            # canonical cut. All invisible cells participate in this test.
            if mask&(1<<axis):selected.append(h)
        if not selected:raise ValueError('rigid.blocked')
        return tuple(selected)

    def material_selection(self,axis,guard=None):
        from cube.cad_copter_clearance import local_cut
        cached=getattr(self,'_clearance_cache',None)
        if cached is None or cached[0]!=self.frames:
            cached=self.frames,{};self._clearance_cache=cached
        if axis in cached[1]:
            result=cached[1][axis]
            if result is None:raise ValueError('rigid.blocked')
            return result
        selected=[];target=self.turn_cut(axis)
        for home,frame in enumerate(self.frames):
            if guard:guard()
            value=self.material_side(home,local_cut(frame,target))
            if value==0:
                cached[1][axis]=None;raise ValueError('rigid.blocked')
            if value>0:selected.append(home)
        result=tuple(selected);cached[1][axis]=result or None
        if not result:raise ValueError('rigid.blocked')
        return result

    def turn_cut(self,axis):return cuts()[axis]

    @staticmethod
    def material_side(home,cut):
        from cube.cad_copter_clearance import side
        return side('flower',home,cut)

    def allowed_amount(self,axis,amount):
        if axis>=12:return abs((amount+30)%60-30)<1e-7
        return any(abs((amount-a+180)%360-180)<1e-7 for a in
                   (0.,180.,JUMBLE,-JUMBLE,180.-JUMBLE,JUMBLE-180.))

    def proposed(self,move,guard=None):
        if (type(move.axis) is not int or move.axis not in range(20)
                or type(move.layer) is not int or move.layer!=0
                or type(move.amount) not in (int,float) or not math.isfinite(move.amount)):
            raise ValueError('rigid.invalid')
        if not self.allowed_amount(move.axis,move.amount):raise ValueError('rigid.blocked')
        selected=set(self.selection(move.axis,guard));angle=math.radians(move.amount)
        turn=tuple(rotate(p,AXES[move.axis],angle) for p in IDENTITY_FRAME)
        following=tuple(multiply(turn,f) if h in selected else f for h,f in enumerate(self.frames))
        # The cut sphere/halfspace is invariant about its turn axis. Whole
        # solids inside it remain disjoint from stationary outside material
        # throughout the motion, including non-cubic intermediate angles.
        return following

    def moves(self):
        return tuple(Move(axis,0,a) for axis in range(20) for a in
                     ((180.,JUMBLE,-JUMBLE,180.-JUMBLE,JUMBLE-180.) if axis<12 else (60.,-60.,120.,-120.)))

    def is_solved(self):
        from cube.crazy_comet import observed_colors
        try:return observed_colors(self)==tuple(f for h,f,p in self.panels)
        except ValueError:return False

    @property
    def geometry(self):
        cached=getattr(self,'_entry_geometry',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        world=self.world_panels();pieces=[[] for _ in self.regions];stickers=[]
        for i,((h,f,p),placed) in enumerate(zip(self.panels,world)):
            normal=transform_frame(self.frames[h],CUBE[f]);shown=max(range(6),key=lambda k:sum(a*b for a,b in zip(normal,CUBE[k])))
            stickers.append(Sticker(h,shown,placed));pieces[h].append(i)
        centres=tuple(mean(tuple(p for i in slots for p in world[i])) if slots else (0.,0.,0.) for slots in pieces)
        try:poses=self._pose_maps()
        except ValueError:
            layers=[]
            for axis in range(20):
                try:members=self.selection(axis)
                except ValueError:members=()
                layers.append((members,))
            layers=tuple(layers)
        else:layers=tuple((tuple(h for h,(_,f,m) in enumerate(poses) if m&(1<<axis)),) for axis in range(20))
        g=Geometry(Spec(self.puzzle_kind,3,CUBE,AXES,(),360,axis_steps=self.turn_steps),
                   tuple(stickers),tuple(map(tuple,pieces)),centres,((),)*20,layers)
        self._entry_geometry=self.frames,g;return g
