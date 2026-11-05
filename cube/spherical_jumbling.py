"""Whole spherical material for the existing Clover and Bauhinia profiles."""
import math
from functools import lru_cache
from cube.edge_jumbling import EdgeJumblingCube,FACTORIES
from cube.planar_twins_state import RecordedTurns
from cube.polyhedral import CUBE,DODECA,EDGE_AXES,Spec,Move,unit,scale,mean,dot,Geometry,Sticker
from cube.curved_partition import SphereCut,shell
from cube.spherical_cells import Arrangement,Plane
from cube.curvy_copter import inverse_point,JUMBLE
from cube.appearance import transform_frame

BAU_JUMBLE=math.degrees(math.asin(.25))+30.


@lru_cache(maxsize=2)
def cuts(kind):
    if kind=='clover':return tuple(SphereCut(scale(n,math.sqrt(2)),1.) for n in EDGE_AXES)
    from cube.rex_dodecahedron import cuts as bauhinia_cuts
    return bauhinia_cuts()


def normals(kind):return CUBE if kind=='clover' else DODECA


def fingerprint(kind):
    import hashlib
    return hashlib.sha256(repr((cuts(kind),layout(kind)[0],layout(kind)[2])).encode('ascii')).hexdigest()


@lru_cache(maxsize=2)
def layout(kind):
    cs=cuts(kind);spec=Spec(kind,3,normals(kind),tuple(unit(c.centre) for c in cs),(),360)
    fragments=shell(spec,cs);visible=tuple(dict.fromkeys(mask for mask,f,p in fragments))
    arrangement=Arrangement(tuple(Plane(n,1.) for n in normals(kind)),cs)
    masks=visible+tuple(sorted(set(arrangement.positive_masks())-set(visible)))
    owners={m:h for h,m in enumerate(masks)}
    return masks,tuple(arrangement.region(m) for m in masks),tuple((owners[m],f,p) for m,f,p in fragments)


@lru_cache(maxsize=32768)
def material_side(kind,home,centre):
    for i,c in enumerate(cuts(kind)):
        if math.dist(centre,c.centre)<1e-8:return 1 if layout(kind)[0][home]&(1<<i) else -1
    return layout(kind)[1][home].side(SphereCut(centre,cuts(kind)[0].radius))


class SphericalJumblingCube(EdgeJumblingCube):
    @property
    def normals(self):return normals(self.puzzle_kind)

    def selection(self,axis,guard=None):
        if type(axis) is not int or axis not in range(len(self.turn_axes)):raise ValueError('rigid.invalid')
        selected=[];cut=cuts(self.puzzle_kind)[axis]
        for h,frame in enumerate(self.frames):
            if guard:guard()
            value=material_side(self.puzzle_kind,h,tuple(round(v,10) for v in inverse_point(frame,cut.centre)))
            if value==0:raise ValueError('rigid.blocked')
            if value>0:selected.append(h)
        if not selected:raise ValueError('rigid.blocked')
        return tuple(selected)

    def shape_weights(self):return (1,)*len(self.frames)

    def moves(self):
        amounts=(180.,JUMBLE,-JUMBLE,180.-JUMBLE,JUMBLE-180.) if self.puzzle_kind=='clover' else (120.,-120.,BAU_JUMBLE,-BAU_JUMBLE,120.-BAU_JUMBLE,BAU_JUMBLE-120.)
        return tuple(Move(a,0,t) for a in range(len(self.turn_axes)) for t in amounts)

    def aligned_frames(self,home):
        if self.puzzle_kind=='clover':return super().aligned_frames(home)
        from cube.mirror_minx import frames
        return frames()

    def frame_aligned(self,home,frame):
        return any(max(abs(a-b) for u,v in zip(frame,r) for a,b in zip(u,v))<1e-7 for r in self.aligned_frames(home))

    @property
    def geometry(self):
        cached=getattr(self,'_geometry',None)
        if cached and cached[0]==self.frames:return cached[1]
        pieces=[[] for _ in self.frames];stickers=[];world=self.world_panels()
        for i,((h,f,p),poly) in enumerate(zip(self.panels,world)):
            normal=transform_frame(self.frames[h],self.normals[f]);shown=max(range(self.color_count),key=lambda f:dot(normal,self.normals[f]))
            pieces[h].append(i);stickers.append(Sticker(h,shown,poly))
        centres=tuple(mean(tuple(p for i in slots for p in world[i])) if slots else (0.,0.,0.) for slots in pieces)
        layers=[]
        for a in range(len(self.turn_axes)):
            try:members=self.selection(a)
            except ValueError:members=()
            layers.append((members,))
        g=Geometry(Spec(self.puzzle_kind,3,self.normals,self.turn_axes,(),360,axis_steps=self.turn_steps),
                   tuple(stickers),tuple(map(tuple,pieces)),centres,((),)*len(self.turn_axes),tuple(layers))
        self._geometry=self.frames,g;return g

    def regular_colours(self):
        self.aligned_permutation()
        from cube.polyhedral import PolyhedralPuzzle
        fixed=PolyhedralPuzzle(self.puzzle_kind,3);world=self.world_panels();used=set();colours=[]
        # Clover's older hand-sampled arcs use a different tessellation. Match
        # whole face patches geometrically, then require a complete bijection.
        for s in fixed.geometry.stickers:
            centre=mean(s.polygon);normal=self.normals[s.face]
            candidates=[(math.dist(centre,mean(p)),i) for i,((h,f,original),p) in enumerate(zip(self.panels,world))
                        if i not in used and math.dist(transform_frame(self.frames[h],self.normals[f]),normal)<1e-7]
            if not candidates:raise ValueError('copter.align_first')
            distance,i=min(candidates)
            if distance>.04:raise ValueError('copter.align_first')
            used.add(i);colours.append(self.paints[i])
        if len(used)!=len(self.panels):raise ValueError('copter.invalid_shape')
        fixed.colors=colours;return fixed


class CloverCube(RecordedTurns, SphericalJumblingCube):
    puzzle_kind='clover'
    color_count=6
    observation_model='clover-spherical-whole-v1'
    layout=staticmethod(lambda:layout('clover'))


class BauhiniaCube(SphericalJumblingCube):
    puzzle_kind='mf8_bauhinia_minx'
    color_count=12
    observation_model='bauhinia-spherical-whole-v1'
    layout=staticmethod(lambda:layout('mf8_bauhinia_minx'))
    turn_axes=tuple(unit(c.centre) for c in cuts('mf8_bauhinia_minx'))
    turn_steps=(120,)*20


FACTORIES.update(clover=CloverCube,mf8_bauhinia_minx=BauhiniaCube)
