"""Drawing3 Twins CSG solids with guarded edge and half-shell turns."""
import math
from cube.flower_copter import FlowerCopterCube
from cube.twins_cad_material import structure,frame_action,transform_group,AXES,DIAGONALS,fingerprint
from cube.polyhedral import CUBE,OCTA,Move,Spec,Geometry,Sticker,mean,dot,rotate
from cube.appearance import ROTATIONS,IDENTITY_FRAME,transform_frame
from cube.curvy_copter import multiply,JUMBLE

SECOND=math.degrees(math.acos(1/math.sqrt(3)))


class TwinsState(FlowerCopterCube):
    puzzle_kind='mf8_twins'
    geometry_profile='drawing3-conditional-csg-jumbling-v1'
    observation_model='mf8-twins-drawing3-regular-v1'
    layout=staticmethod(structure)
    turn_axes=AXES
    turn_steps=(180,)*12+(60,)*8

    def __init__(self,frames=None,paints=None):
        super().__init__(frames,paints);self.solids=self.regions

    @property
    def geometry_fingerprint(self):return fingerprint()

    def observation_data(self):
        result=super().observation_data();result['source']=fingerprint();return result

    @classmethod
    def from_observation(cls,value):
        if type(value) is not dict or value.get('source')!=fingerprint():raise ValueError('twins.legacy_entry')
        return super().from_observation(value)

    def _pose_maps(self):
        cached=getattr(self,'_cached_pose_maps',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        owners={g:h for h,g in enumerate(self.signatures)};result=[]
        for g,frame in zip(self.signatures,self.frames):
            action=frame_action(frame);target=transform_group(g,action)
            if target not in owners:raise ValueError('copter.invalid_shape')
            result.append((owners[target],action[3],target))
        if sorted(h for h,f,g in result)!=list(range(len(self.regions))):raise ValueError('copter.invalid_shape')
        result=tuple(result);self._cached_pose_maps=self.frames,result;return result

    def selection(self,axis,guard=None):
        if type(axis) is not int or axis not in range(20):raise ValueError('rigid.invalid')
        try:poses=self._pose_maps()
        except ValueError as exc:
            if str(exc)!='twins.regular_only':raise
            return self.material_selection(axis,guard)
        selected=[]
        for h,(target,faces,g) in enumerate(poses):
            if guard:guard()
            if axis<12:inside=bool(g[0]&(1<<axis))
            else:
                n=OCTA[axis-12];index=next(i for i,d in enumerate(DIAGONALS) if abs(dot(n,d))>1-1e-8)
                inside=bool(g[1]&(1<<index)) if dot(n,DIAGONALS[index])<0 else not bool(g[1]&(1<<index))
            if inside:selected.append(h)
        return tuple(selected)

    def turn_cut(self,axis):
        if axis<12:
            from cube.twins_cad_material import cuts
            return cuts()[axis]
        from cube.spherical_cells import Plane
        return Plane(tuple(-v for v in AXES[axis]),0.)

    @staticmethod
    def material_side(home,cut):
        from cube.cad_copter_clearance import side
        return side('twins',home,cut)

    def moves(self):
        return tuple(Move(axis,0,a) for axis in range(20) for a in
                     ((180.,JUMBLE,-JUMBLE,180.-JUMBLE,JUMBLE-180.,SECOND,-SECOND,180.-SECOND,SECOND-180.)
                      if axis<12 else (60.,-60.,120.,-120.)))

    def allowed_amount(self,axis,amount):
        if axis>=12:return super().allowed_amount(axis,amount)
        return any(abs((amount-a+180)%360-180)<1e-7 for a in
                   (0.,180.,JUMBLE,-JUMBLE,180.-JUMBLE,JUMBLE-180.,SECOND,-SECOND,180.-SECOND,SECOND-180.))

    def aligned_frames(self,home):return ROTATIONS

    def frame_aligned(self,home,frame):
        try:frame_action(frame);return True
        except ValueError:return False

    def complete_hidden(self):
        """Fit unobservable whole CSG cells into the remaining regular slots."""
        visible={h for h,f,p in self.panels};owners={g:h for h,g in enumerate(self.signatures)}
        used=set();frames=list(self.frames)
        for h in visible:
            target=owners[transform_group(self.signatures[h],frame_action(frames[h]))]
            if target in used:raise ValueError('copter.invalid_shape')
            used.add(target)
        for h in range(len(frames)):
            if h in visible:continue
            for frame in (frames[h],)+ROTATIONS:
                target=owners[transform_group(self.signatures[h],frame_action(frame))]
                if target not in used:frames[h]=frame;used.add(target);break
            else:raise ValueError('copter.invalid_shape')
        return type(self)(frames,self.paints)

    @property
    def geometry(self):
        cached=getattr(self,'_entry_geometry',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        world=self.world_panels();pieces=[[] for _ in self.regions];stickers=[]
        for i,((h,f,p),placed) in enumerate(zip(self.panels,world)):
            normal=transform_frame(self.frames[h],CUBE[f]);shown=max(range(6),key=lambda k:dot(normal,CUBE[k]))
            stickers.append(Sticker(h,shown,placed));pieces[h].append(i)
        centres=tuple(mean(tuple(p for i in slots for p in world[i])) if slots else (0.,0.,0.) for slots in pieces)
        layers=[]
        for axis in range(20):
            try:members=self.selection(axis)
            except ValueError:members=()
            layers.append((members,))
        layers=tuple(layers)
        g=Geometry(Spec(self.puzzle_kind,3,CUBE,AXES,(),360,axis_steps=self.turn_steps),
                   tuple(stickers),tuple(map(tuple,pieces)),centres,((),)*20,layers)
        self._entry_geometry=self.frames,g;return g
