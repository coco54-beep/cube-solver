"""Retained planar rhombic-dodecahedral research model, separate from Rua.

This does not match the requested LanLan shell. The initial implementation
was misidentified as Crazy Comet; its module and asset filenames are retained
for checkpoint compatibility, while the public kind/name now identify research.
Every material cell is a closed convex solid; turns test all its vertices.
"""
from functools import lru_cache
import math
from cube.polyhedral import EDGE_AXES,CUBE,Spec,Geometry,Sticker,Move,body,dot,scale,mean,key,rotate,cross,unit
from cube.appearance import IDENTITY_FRAME,ROTATIONS,transform_frame
from cube.curvy_copter import CopterState,JUMBLE,multiply,inverse_point
from cube.copter_input import CopterCube
from cube.mirror_tower import _clip_solid

CUT=.75
NORMALS=EDGE_AXES


@lru_cache(maxsize=512)
def vertices(faces):return tuple({key(v):v for poly,color in faces for v in poly}.values())


def volume(faces):
    return abs(sum(dot(poly[0],cross(poly[i],poly[i+1]))/6
                   for poly,color in faces for i in range(1,len(poly)-1)))


@lru_cache(maxsize=1)
def structure():
    cells=[(0,tuple((poly,i) for i,poly in enumerate(body(NORMALS))))]
    for axis,normal in enumerate(EDGE_AXES):
        following=[]
        for mask,faces in cells:
            values=[dot(normal,p) for p in vertices(faces)]
            if max(values)<=CUT+1e-9:following.append((mask,faces));continue
            if min(values)>=CUT-1e-9:following.append((mask|(1<<axis),faces));continue
            for positive in (False,True):
                kept=tuple(_clip_solid(faces,scale(normal,-1) if positive else normal,-CUT if positive else CUT))
                if volume(kept)>1e-9:following.append((mask|(1<<axis) if positive else mask,kept))
        cells=following
    cells.sort(key=lambda cell:(cell[0]==0,cell[0]))
    masks=tuple(mask for mask,faces in cells);solids=tuple(faces for mask,faces in cells)
    panels=tuple((home,color,poly) for home,faces in enumerate(solids) for poly,color in faces if color>=0)
    return masks,solids,panels


class CometCube(CopterCube):
    puzzle_kind='planar_rhombic_12'
    color_count=12
    geometry_profile='planar-rhombic'
    cut=CUT

    @staticmethod
    def layout():return structure()

    @staticmethod
    def panel_normal(face,poly):return NORMALS[face]

    def observation_data(self):
        return dict(model='crazy-comet-planar',version=1,frames=self.frames,paints=self.paints)

    @classmethod
    def from_observation(cls,data):
        if (type(data) is not dict or data.get('model')!='crazy-comet-planar'
                or type(data.get('version')) is not int or data.get('version')!=1
                or type(data.get('frames')) not in (list,tuple)
                or type(data.get('paints')) not in (list,tuple)):
            raise ValueError('rigid.invalid')
        return cls(data['frames'],data['paints'])

    def __init__(self,frames=None,paints=None):
        self.signatures,self.solids,self.panels=self.layout();self.regions=self.solids
        try:
            self.frames=(tuple(tuple(tuple(float(v) for v in column) for column in f) for f in frames)
                         if frames is not None else (IDENTITY_FRAME,)*len(self.solids))
            self.paints=tuple(paints) if paints is not None else tuple(face for home,face,poly in self.panels)
        except (TypeError,ValueError,OverflowError):raise ValueError('rigid.invalid') from None
        if len(self.frames)!=len(self.solids) or len(self.paints)!=len(self.panels):raise ValueError('rigid.invalid')
        for f in self.frames:
            if (len(f)!=3 or any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in f)
                    or any(abs(dot(a,b)-(i==j))>1e-7 for i,a in enumerate(f) for j,b in enumerate(f))
                    or dot(cross(f[0],f[1]),f[2])<1-1e-7):raise ValueError('rigid.invalid')
        if any(type(c) is not int or c not in range(-1,self.color_count) for c in self.paints):raise ValueError('rigid.invalid')

    def paint(self,slot,color):
        if type(slot) is not int or slot not in range(len(self.panels)):raise ValueError('rigid.invalid')
        if type(color) is not int or color not in range(-1,self.color_count):raise ValueError('rigid.invalid')
        paints=list(self.paints);paints[slot]=color;self.paints=tuple(paints)

    def selection(self,axis,guard=None):
        if type(axis) is not int or axis not in range(12):raise ValueError('rigid.invalid')
        normal=EDGE_AXES[axis];selected=[]
        for home,(faces,frame) in enumerate(zip(self.solids,self.frames)):
            if guard:guard()
            local=inverse_point(frame,normal);values=[dot(local,p) for p in vertices(faces)]
            if min(values)>=self.cut-1e-8:selected.append(home)
            elif max(values)>self.cut+1e-8:raise ValueError('rigid.blocked')
        if not selected:raise ValueError('rigid.blocked')
        return tuple(selected)

    def proposed(self,move,guard=None):
        if (type(move.layer) is not int or move.layer!=0 or type(move.amount) not in (int,float)
                or not math.isfinite(move.amount)):raise ValueError('rigid.invalid')
        selected=set(self.selection(move.axis,guard))
        turn=tuple(rotate(v,EDGE_AXES[move.axis],math.radians(move.amount)) for v in IDENTITY_FRAME)
        return tuple(multiply(turn,f) if home in selected else f for home,f in enumerate(self.frames))

    def aligned_permutation(self):
        indices={key(n):i for i,n in enumerate(NORMALS)};owners={mask:i for i,mask in enumerate(self.signatures)}
        slots={(home,face):i for i,(home,face,p) in enumerate(self.panels)};mapping=[]
        for mask,frame in zip(self.signatures,self.frames):
            proper=next((r for r in ROTATIONS if max(abs(a-b) for u,v in zip(frame,r) for a,b in zip(u,v))<1e-7),None)
            if proper is None:raise ValueError('copter.align_first')
            faces=tuple(indices[key(transform_frame(proper,n))] for n in NORMALS)
            target=sum(1<<faces[i] for i in range(12) if mask&(1<<i))
            if target not in owners:raise ValueError('copter.invalid_shape')
            mapping.append((owners[target],faces))
        if sorted(p for p,f in mapping)!=list(range(len(mapping))):raise ValueError('copter.invalid_shape')
        result=tuple(slots[mapping[home][0],mapping[home][1][face]] for home,face,poly in self.panels)
        if sorted(result)!=list(range(len(result))):raise ValueError('copter.invalid_shape')
        return result

    def is_solved(self):
        try:colors=observed_colors(self)
        except ValueError:return False
        return colors==tuple(face for home,face,p in self.panels)

    @property
    def geometry(self):
        cached=getattr(self,'_entry_geometry',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        world=self.world_panels();pieces=[[] for _ in self.solids];stickers=[]
        for i,((home,face,poly),placed) in enumerate(zip(self.panels,world)):
            normal=transform_frame(self.frames[home],self.panel_normal(face,poly));shown=max(range(12),key=lambda f:dot(normal,NORMALS[f]))
            pieces[home].append(i);stickers.append(Sticker(home,shown,placed))
        centres=tuple(mean(tuple(transform_frame(frame,p) for p in vertices(faces))) for frame,faces in zip(self.frames,self.solids))
        layers=[]
        for axis in range(12):
            try:selected=self.selection(axis)
            except ValueError:selected=()
            layers.append((selected,))
        g=Geometry(Spec(self.puzzle_kind,3,NORMALS,EDGE_AXES,(self.cut,),360,axis_steps=(180,)*12),
                   tuple(stickers),tuple(map(tuple,pieces)),centres,((),)*12,tuple(layers))
        self._entry_geometry=(self.frames,g);return g


def observed_colors(cube):
    result=[None]*len(cube.panels)
    for source,target in enumerate(cube.aligned_permutation()):result[target]=cube.paints[source]
    return tuple(result)


@lru_cache(maxsize=1)
def generators():
    from itertools import combinations,product
    cube=CometCube();found={}
    words=[(Move(axis,0,180.),) for axis in range(12)]
    for target,n in enumerate(EDGE_AXES):
        neighbours=[i for i,a in enumerate(EDGE_AXES) if abs(dot(a,n)-.5)<1e-8]
        for a,b in combinations(neighbours,2):
            if dot(EDGE_AXES[a],EDGE_AXES[b])>-.49:continue
            for sa,sb in product((-1,1),repeat=2):
                words.append((Move(a,0,sa*JUMBLE),Move(b,0,sb*JUMBLE),Move(target,0,180.),
                              Move(b,0,-sb*JUMBLE),Move(a,0,-sa*JUMBLE)))
    for word in words:
        work=cube.clone()
        try:
            work.apply_moves(word);action=work.aligned_permutation()
        except ValueError:continue
        if any(action[action[s]]!=s for s in range(len(action))):raise ValueError('Comet macro is not an involution')
        if action not in found or len(word)<len(found[action]):found[action]=word
    return tuple(found.items())


def scrambled(seed=None,length=30,cancel=None,jumble=True):
    from random import Random
    from time import monotonic
    rng=Random(seed);cube=CometCube();options=generators();previous=None;deadline=monotonic()+12
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()>deadline:raise TimeoutError('copter.scramble_timeout')
    for _ in range(length):
        guard();index=rng.choice([i for i in range(len(options)) if i!=previous]);previous=index
        for move in options[index][1]:cube.apply_move(move,guard)
    for _ in range(6 if jumble else 0):
        choices=list(cube.moves());rng.shuffle(choices)
        for move in choices:
            guard()
            try:cube.apply_move(move,guard);break
            except ValueError:continue
    return cube
