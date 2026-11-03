"""Independent regular Master Clover kinematics and bonded observations.

Closed shallow/deep half-turns are supported. Photographic arcs do not
establish an internal continuous cut, so partial turns are rejected.
"""
import math,json,zlib,hashlib
from pathlib import Path
from functools import lru_cache
from cube.copter_input import CopterCube
from cube.appearance import ROTATIONS,IDENTITY_FRAME,transform_frame
from cube.curvy_copter import multiply
from cube.polyhedral import CUBE,EDGE_AXES,Move,Spec,Geometry,Sticker,dot,cross,rotate,scale


def centre(poly,normal):
    origin=poly[0];weighted=[0.,0.,0.];total=0.
    for a,b in zip(poly[1:-1],poly[2:]):
        x=tuple(v-w for v,w in zip(a,origin));y=tuple(v-w for v,w in zip(b,origin))
        area=dot(cross(x,y),normal)
        for j in range(3):weighted[j]+=area*(origin[j]+a[j]+b[j])/3
        total+=area
    return tuple(v/total for v in weighted)


@lru_cache(maxsize=1)
def shell_data():
    data=json.loads(zlib.decompress((Path(__file__).parent/'data/master_clover_shell.bin').read_bytes()))
    if data['version']!=1 or data['profile']!='photo-regular-shell-v1':raise ValueError('Master Clover shell mismatch')
    return data


@lru_cache(maxsize=1)
def structure():
    panels=tuple((h,f,tuple(tuple(v) for v in p)) for h,f,p in shell_data()['panels'])
    if len(panels)!=120 or set(h for h,f,p in panels)!=set(range(68)):raise ValueError('Invalid Master Clover fields')
    return tuple(range(68)),tuple(range(68)),panels


def source_key():
    return hashlib.sha256((Path(__file__).parent/'data/master_clover_shell.bin').read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def placement_maps():
    panels=structure()[2];centres=tuple(centre(p,CUBE[f]) for h,f,p in panels);rows=[]
    for frame in ROTATIONS:
        row=[]
        for (h,f,p),c in zip(panels,centres):
            target=transform_frame(frame,c);normal=transform_frame(frame,CUBE[f])
            candidates=[i for i,(k,g,q) in enumerate(panels) if dot(CUBE[g],normal)>1-1e-8]
            i=min(candidates,key=lambda i:math.dist(target,centres[i]))
            if math.dist(target,centres[i])>1e-7:raise ValueError('Master Clover shell is not rotation invariant')
            row.append(i)
        if sorted(row)!=list(range(120)):raise ValueError('Invalid Master Clover placement map')
        rows.append(tuple(row))
    return tuple(rows)


class MasterCloverCube(CopterCube):
    puzzle_kind='lanlan_master_clover'
    geometry_profile='photo-regular-double-edge'
    observation_model='lanlan-master-clover-regular-v1'
    layout=staticmethod(structure)
    turn_axes=EDGE_AXES
    turn_steps=(180,)*12

    def observation_data(self):return dict(model=self.observation_model,version=1,frames=self.frames,paints=self.paints)

    @classmethod
    def from_observation(cls,data):
        if (type(data) is not dict or data.get('model')!=cls.observation_model
                or type(data.get('version')) is not int or data['version']!=1
                or 'frames' not in data or 'paints' not in data):raise ValueError('rigid.invalid')
        return cls(data['frames'],data['paints'])

    def _placements(self):
        cached=getattr(self,'_master_placements',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        result=[]
        for frame in self.frames:
            proper=tuple(tuple(round(v) for v in col) for col in frame)
            if proper not in ROTATIONS or any(abs(a-b)>1e-7 for u,v in zip(proper,frame) for a,b in zip(u,v)):
                raise ValueError('master_clover.regular_only')
            result.append(ROTATIONS.index(proper))
        result=tuple(result);self._master_placements=self.frames,result;return result

    def aligned_permutation(self):
        cached=getattr(self,'_master_permutation',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        placements=self._placements();maps=placement_maps()
        result=tuple(maps[placements[h]][i] for i,(h,f,p) in enumerate(self.panels))
        if sorted(result)!=list(range(120)):raise ValueError('copter.invalid_shape')
        self._master_permutation=self.frames,result;return result

    def validate_pose(self):self.aligned_permutation()

    def frame_aligned(self,home,frame):
        return any(max(abs(a-b) for u,v in zip(frame,r) for a,b in zip(u,v))<1e-7 for r in ROTATIONS)

    def aligned_frames(self,home):return ROTATIONS

    def shape_weights(self):return (1,)*68

    def selection(self,axis,layer=0,guard=None):
        if type(axis) is not int or axis not in range(12) or type(layer) is not int or layer not in (0,1):
            raise ValueError('rigid.invalid')
        permutation=self.aligned_permutation();selected=set();roles=shell_data()['roles'];corners=shell_data()['corners']
        for h in range(8):
            if guard:guard()
            if layer==0 and dot(transform_frame(self.frames[h],corners[h]),EDGE_AXES[axis])>1.4:selected.add(h)
        for source,(h,f,p) in enumerate(self.panels):
            if h<8:continue
            target=permutation[source];role=roles[target]
            if role['kind']=='edge':active=axis==role['axes'][0]
            elif layer==0:active=axis in role['axes']
            else:
                c=centre(self.panels[target][2],CUBE[self.panels[target][1]])
                active=axis==max(role['axes'],key=lambda a:dot(EDGE_AXES[a],c))
            if active:selected.add(h)
        return tuple(sorted(selected))

    def proposed(self,move,guard=None):
        if type(move.amount) not in (int,float) or not math.isfinite(move.amount):raise ValueError('rigid.invalid')
        if abs((move.amount+90)%180-90)>1e-7:raise ValueError('master_clover.regular_only')
        selected=set(self.selection(move.axis,move.layer,guard))
        turn=tuple(rotate(v,EDGE_AXES[move.axis],math.radians(move.amount)) for v in IDENTITY_FRAME)
        return tuple(multiply(turn,f) if h in selected else f for h,f in enumerate(self.frames))

    def moves(self):return tuple(Move(a,l,180.) for a in range(12) for l in (0,1))

    def is_solved(self):
        from cube.crazy_comet import observed_colors
        try:return observed_colors(self)==tuple(f for h,f,p in self.panels)
        except ValueError:return False

    @property
    def geometry(self):
        cached=getattr(self,'_master_geometry',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        stickers=[];pieces=[[] for _ in range(68)];centres=[]
        for i,((h,f,p),q) in enumerate(zip(self.panels,self.world_panels())):
            normal=transform_frame(self.frames[h],CUBE[f]);shown=max(range(6),key=lambda k:dot(normal,CUBE[k]))
            stickers.append(Sticker(h,shown,q));pieces[h].append(i)
        for ids in pieces:
            points=[centre(stickers[i].polygon,CUBE[stickers[i].face]) for i in ids]
            centres.append(tuple(sum(p[j] for p in points)/len(points) for j in range(3)))
        try:layers=tuple(tuple(self.selection(a,l) for l in (0,1)) for a in range(12))
        except ValueError:layers=(((),()),)*12
        g=Geometry(Spec(self.puzzle_kind,3,CUBE,EDGE_AXES,(),360,axis_steps=(180,)*12),
                   tuple(stickers),tuple(map(tuple,pieces)),tuple(centres),((),)*12,layers)
        self._master_geometry=self.frames,g;return g
