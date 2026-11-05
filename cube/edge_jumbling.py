"""Whole plane-cut material for Helicopter and Rua, including hidden cells."""
import math
from functools import lru_cache
from cube.polyhedral import CUBE,OCTA,EDGE_AXES,Move,Spec,Geometry,Sticker,body,body_faces,dot,mean,key
from cube.appearance import ROTATIONS,transform_frame
from cube.planar_twins_state import PlanarTwinsState,RecordedTurns
from cube.twins_material import partition
from cube.crazy_comet import vertices
from cube.curvy_copter import JUMBLE

KINDS=('helicopter','rua','helicopter_14')


def polygon_key(poly):return tuple(sorted(tuple(round(v,7) for v in p) for p in poly))


@lru_cache(maxsize=3)
def layout(kind):
    normals=CUBE if kind=='helicopter' else EDGE_AXES
    bound=1/math.sqrt(2) if kind=='helicopter' else .5
    if kind=='helicopter_14':
        from cube.lanlan_polyhedra import specification
        polygons=body_faces(specification(kind,3));bound=1/math.sqrt(2)
    else:polygons=body(normals)
    cells=(tuple((p,f) for f,p in enumerate(polygons)),)
    for n in EDGE_AXES:cells=partition(cells,n,bound)
    panels=tuple((h,f,p) for h,cell in enumerate(cells) for p,f in cell if f>=0)
    return tuple(range(len(cells))),cells,panels


class EdgeJumblingCube(PlanarTwinsState):
    turn_axes=EDGE_AXES
    turn_steps=(180,)*12
    geometry_profile='whole-plane-cells-jumbling-v1'

    def layout(self):return layout(self.puzzle_kind)

    @property
    def normals(self):return CUBE if self.puzzle_kind=='helicopter' else EDGE_AXES

    def panel_normal(self,face,poly):return self.normals[face]

    def aligned_frames(self,home):return ROTATIONS

    def frame_aligned(self,home,frame):
        return any(max(abs(a-b) for u,v in zip(frame,r) for a,b in zip(u,v))<1e-7 for r in ROTATIONS)

    def validate_pose(self):
        try:self.aligned_permutation()
        except ValueError as e:
            if str(e)!='copter.align_first':raise

    def moves(self):
        return tuple(Move(a,0,t) for a in range(12) for t in (180.,JUMBLE,-JUMBLE,180.-JUMBLE,JUMBLE-180.))

    def aligned_permutation(self):
        slots={polygon_key(p):i for i,(h,f,p) in enumerate(self.panels)};result=[]
        for h,f,p in self.panels:
            target=slots.get(polygon_key(tuple(transform_frame(self.frames[h],v) for v in p)))
            if target is None:raise ValueError('copter.align_first')
            result.append(target)
        if sorted(result)!=list(range(len(result))):raise ValueError('copter.invalid_shape')
        return tuple(result)

    @property
    def geometry(self):
        cached=getattr(self,'_geometry',None)
        if cached and cached[0]==self.frames:return cached[1]
        pieces=[[] for _ in self.frames];stickers=[];world=self.world_panels()
        for i,((h,f,p),poly) in enumerate(zip(self.panels,world)):
            normal=transform_frame(self.frames[h],self.normals[f]);shown=max(range(len(self.normals)),key=lambda f:dot(normal,self.normals[f]))
            pieces[h].append(i);stickers.append(Sticker(h,shown,poly))
        layers=[]
        for a in range(12):
            try:members=self.selection(a)
            except ValueError:members=()
            layers.append((members,))
        centres=tuple(transform_frame(f,mean(vertices(s))) for f,s in zip(self.frames,self.solids))
        g=Geometry(Spec(self.puzzle_kind,3,self.normals,EDGE_AXES,(),360,axis_steps=self.turn_steps),
                   tuple(stickers),tuple(map(tuple,pieces)),centres,((),)*12,tuple(layers))
        self._geometry=self.frames,g;return g

    def regular_colours(self):
        from cube.polyhedral import PolyhedralPuzzle
        fixed=PolyhedralPuzzle(self.puzzle_kind,3)
        actual={polygon_key(p):self.paints[i] for i,p in enumerate(self.world_panels())}
        try:fixed.colors=[actual[polygon_key(s.polygon)] for s in fixed.geometry.stickers]
        except KeyError:raise ValueError('copter.align_first') from None
        return fixed

    def is_solved(self):
        try:return self.regular_colours().is_solved()
        except ValueError:return False


class HelicopterCube(RecordedTurns, EdgeJumblingCube):
    layout=staticmethod(lambda:layout('helicopter'))
    puzzle_kind='helicopter'
    observation_model='helicopter-whole-material-v1'
    color_count=6
    cut_bounds=(1/math.sqrt(2),)*12


class RuaCube(EdgeJumblingCube):
    layout=staticmethod(lambda:layout('rua'))
    puzzle_kind='rua'
    observation_model='rua-whole-material-v1'
    color_count=12
    cut_bounds=(.5,)*12


class Helicopter14Cube(EdgeJumblingCube):
    layout=staticmethod(lambda:layout('helicopter_14'))
    puzzle_kind='helicopter_14'
    observation_model='helicopter-14-whole-material-v1'
    color_count=7
    cut_bounds=(1/math.sqrt(2),)*12
    normals=CUBE+OCTA

    def __init__(self,frames=None,paints=None):
        # Eight distinct physical triangular caps share one gold colour.
        if paints is None:paints=tuple(min(f,6) for h,f,p in self.layout()[2])
        super().__init__(frames,paints)

    def aligned_permutation(self):
        cached=getattr(self,'_full_alignment',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        result=super().aligned_permutation()
        homes={polygon_key(vertices(s)):h for h,s in enumerate(self.solids)};owners=[]
        for frame,solid in zip(self.frames,self.solids):
            target=homes.get(polygon_key(tuple(transform_frame(frame,p) for p in vertices(solid))))
            if target is None:raise ValueError('copter.align_first')
            owners.append(target)
        if sorted(owners)!=list(range(len(self.solids))):raise ValueError('copter.invalid_shape')
        self._full_alignment=self.frames,result;return result


FACTORIES={'helicopter':HelicopterCube,'rua':RuaCube,'helicopter_14':Helicopter14Cube}


def scrambled(kind,seed=None,length=30,cancel=None):
    if kind=='helicopter_14':
        from cube.helicopter_14_aligned import scrambled as scramble_fourteen
        return scramble_fourteen(seed,length,cancel)
    from random import Random
    from time import monotonic
    if kind not in FACTORIES:from cube import spherical_jumbling
    rng=Random(seed);cube=FACTORIES[kind]();previous=-1;deadline=monotonic()+15
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()>deadline:raise TimeoutError('copter.scramble_timeout')
    for _ in range(length):
        guard();a=rng.choice([a for a in range(len(cube.turn_axes)) if a!=previous]);cube.apply_move(Move(a,0,cube.turn_steps[a]),guard);previous=a
    if length:
        if kind=='mf8_bauhinia_minx':
            from cube.spherical_jumbling import BAU_JUMBLE
            a=rng.randrange(20);prepared=set(cube.selection(a));cube.apply_move(Move(a,0,rng.choice((BAU_JUMBLE,-BAU_JUMBLE))),guard)
            choices=list(range(20));rng.shuffle(choices)
            for b in choices:
                if b==a:continue
                try:members=set(cube.selection(b,guard))
                except ValueError:continue
                if members&prepared:cube.apply_move(Move(b,0,120.),guard);break
        else:
            from cube.cad_copter_scramble import deform
            deform(cube,rng,cancel,deadline)
    return cube
