"""Radius-one Butterflower, with whole-material guarded petal exchanges."""
import math
from functools import lru_cache
from cube.flower_copter import FlowerCopterCube
from cube.butterflower_material import structure,cuts,AXES
from cube.curvy_copter import JUMBLE,inverse_point,multiply
from cube.polyhedral import CUBE,Move,rotate
from cube.appearance import IDENTITY_FRAME,ROTATIONS


@lru_cache(maxsize=1)
def material_regions():
    from cube.spherical_cells import Arrangement,Plane
    arrangement=Arrangement(tuple(Plane(n,1.) for n in CUBE),cuts())
    return tuple(arrangement.region(mask) for mask in structure()[0])


@lru_cache(maxsize=16384)
def material_side(home,centre,radius):
    # Match an existing cut before doing analytic extrema enumeration. This
    # also keeps canonical replay and cached jumble poses cheap on phones.
    from cube.curved_partition import SphereCut
    for axis,cut in enumerate(cuts()):
        if abs(radius-cut.radius)<1e-9 and math.dist(centre,cut.centre)<1e-8:
            return 1 if structure()[0][home]&(1<<axis) else -1
    return material_regions()[home].side(SphereCut(centre,radius))


class ButterflowerCube(FlowerCopterCube):
    puzzle_kind='lanlan_butterflower'
    geometry_profile='radius-one-spheres-jumbling'
    observation_model='lanlan-butterflower-radius-one-regular-v1'
    layout=staticmethod(structure)
    turn_steps=(180,)*12+(120,)*8

    def turn_cut(self,axis):return cuts()[axis]

    @staticmethod
    def material_side(home,cut):return material_side(home,cut.centre,cut.radius)

    def allowed_amount(self,axis,amount):
        return axis<12 or abs((amount+60)%120-60)<1e-7

    def _pose_maps(self):
        try:return super()._pose_maps()
        except ValueError as exc:
            if str(exc)=='flower.regular_only':raise ValueError('copter.align_first') from None
            raise

    def validate_pose(self):
        # Incomplete shape entry must reach the cancellable shape search.
        # A non-cubic frame is not itself an illegal physical observation.
        try:self._pose_maps()
        except ValueError as exc:
            if str(exc)!='copter.align_first':raise

    def selection(self,axis,guard=None):
        if type(axis) is not int or axis not in range(20):raise ValueError('rigid.invalid')
        try:return super().selection(axis,guard)
        except ValueError as exc:
            if str(exc)!='copter.align_first':raise
        target=cuts()[axis];selected=[]
        for home,frame in enumerate(self.frames):
            if guard:guard()
            centre=tuple(round(v,10) for v in inverse_point(frame,target.centre))
            side=material_side(home,centre,target.radius)
            if side==0:raise ValueError('rigid.blocked')
            if side>0:selected.append(home)
        if not selected:raise ValueError('rigid.blocked')
        return tuple(selected)

    def proposed(self,move,guard=None):
        if (type(move.axis) is not int or move.axis not in range(20)
                or type(move.layer) is not int or move.layer!=0
                or type(move.amount) not in (int,float) or not math.isfinite(move.amount)):
            raise ValueError('rigid.invalid')
        if move.axis>=12 and abs((move.amount+60)%120-60)>1e-7:raise ValueError('rigid.blocked')
        selected=set(self.selection(move.axis,guard))
        turn=tuple(rotate(p,AXES[move.axis],math.radians(move.amount)) for p in IDENTITY_FRAME)
        return tuple(multiply(turn,f) if h in selected else f for h,f in enumerate(self.frames))

    def moves(self):
        return tuple(Move(a,0,t) for a in range(20) for t in
                     ((180.,JUMBLE,-JUMBLE,180.-JUMBLE,JUMBLE-180.) if a<12 else (120.,-120.)))

    def aligned_frames(self,home):return ROTATIONS

    def frame_aligned(self,home,frame):
        return any(max(abs(a-b) for u,v in zip(frame,r) for a,b in zip(u,v))<1e-7 for r in ROTATIONS)

    def shape_weights(self):
        # The search heuristic never participates in clearance decisions.
        # Weight hidden cells too: an uncoloured carrier still blocks a cut.
        return (1,)*len(self.frames)

    @property
    def geometry(self):
        cached=getattr(self,'_butter_entry_geometry',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        g=super().geometry
        try:self._pose_maps()
        except ValueError as exc:
            if str(exc)!='copter.align_first':raise
            from dataclasses import replace
            layers=[]
            for axis in range(20):
                try:members=self.selection(axis)
                except ValueError:members=()
                layers.append((members,))
            g=replace(g,layers=tuple(layers))
        self._butter_entry_geometry=self.frames,g
        return g
