"""Closed curved Flower reference, sharing entry colours and seams."""
import math
from functools import lru_cache
from cube.flower_material import structure,cuts
from cube.curved_partition import partition
from cube.spherical_cells import Plane
from cube.polyhedral import CUBE,add,scale,dot,cross,unit,mean,triangulate,clip
from renderer.twins_view import TwinsView
from renderer.copter_view import CopterTwistView
from cube.spherical_surfaces import outline


def sphere_face(mask,index,cut_set=None,bounds_normals=CUBE):
    cut_set=cuts() if cut_set is None else cut_set
    sphere=cut_set[index];planes=[(n,1-dot(n,sphere.centre)) for n in bounds_normals]
    for j,other in enumerate(cut_set):
        if j==index:continue
        if isinstance(other,Plane):normal=other.normal;bound=other.bound-dot(normal,sphere.centre)
        else:
            delta=add(other.centre,scale(sphere.centre,-1));distance=math.sqrt(dot(delta,delta))
            normal=scale(delta,-1/distance)
            bound=(other.radius**2-sphere.radius**2-distance**2)/(2*distance)
        if not mask&(1<<j):normal=scale(normal,-1);bound=-bound
        planes.append((normal,bound))
    active=[]
    for normal,bound in planes:
        if bound<=-sphere.radius+1e-9:return ()
        if bound<sphere.radius-1e-9:active.append((normal,bound))
    try:boundary=outline(tuple(active),sphere.radius,segments=48)
    except ValueError as error:
        if str(error)=='Spherical panel has no boundary':return ()
        raise
    if len(boundary)<3:return ()
    # Some internal patches are crescents: a fan about their average cuts
    # across another cell. Ear-clip a gnomonic projection instead. Refine
    # each ear on the sphere and clip the display chords to every analytic
    # halfspace, including the cube faces. Picking/clearance never use these
    # display triangles.
    direction=unit(mean(boundary));seed=min(CUBE,key=lambda n:abs(dot(n,direction)))
    u=unit(cross(direction,seed));v=cross(direction,u);projected={}
    for p in boundary:
        height=dot(p,direction)
        if height<=1e-8:raise ValueError('Flower spherical patch exceeds a projection hemisphere')
        projected[(dot(p,u)/height,dot(p,v)/height,0.)]=p
    result=[];sign=1 if mask&(1<<index) else -1
    for ear in triangulate(tuple(projected),(0.,0.,1.)):
        corners=tuple(projected[p] for p in ear);hub=scale(unit(mean(corners)),sphere.radius)
        for a,b in zip(corners,corners[1:]+corners[:1]):
            poly=(hub,a,b)
            for normal,bound in active:
                poly=clip(poly,normal,bound)
                if not poly:break
            if not poly:continue
            normal=scale(unit(mean(poly)),sign)
            points=tuple(add(sphere.centre,p) for p in poly)
            result.extend((tri,normal,-1) for tri in triangulate(points,normal))
    return tuple(result)



def build_surfaces(profile=None):
    masks,regions,panels=(structure() if profile is None else profile.structure());result=[]
    cut_set=cuts() if profile is None else profile.cuts()
    for home,mask in enumerate(masks):
        row=[]
        for slot,(h,face,p) in enumerate(panels):
            if home==h:row.extend((t,CUBE[face],slot,-1) for t in triangulate(p,CUBE[face]))
        for i in range(len(cut_set)):row.extend((t,n,slot,i) for t,n,slot in sphere_face(mask,i,cut_set))
        # Avoid depth fighting where a curved internal patch meets a flat
        # coloured face. This tiny display-only inset changes no material,
        # paint polygon, picking boundary or turn selection.
        result.append(tuple((tuple(scale(p,.99999) for p in tri),n,slot,axis) if slot<0 else (tri,n,slot,axis)
                            for tri,n,slot,axis in row))
    return tuple(result)


@lru_cache(maxsize=1)
def skin_data():
    from cube import flower_material
    return load_skin_data(flower_material,'flower_regular_skin.bin')


def load_skin_data(profile,filename):
    import json,zlib,struct
    from pathlib import Path
    payload=zlib.decompress((Path(__file__).resolve().parents[1]/'cube/data'/filename).read_bytes())
    size=struct.unpack_from('<I',payload)[0];data=json.loads(payload[4:4+size]);offset=4+size
    if data['version']!=3 or data['source']!=profile.fingerprint() or len(data['counts'])!=len(profile.structure()[0]):
        raise ValueError('Flower display cache does not match its material')
    pools=[]
    for count in (data['points'],data['normals']):
        end=offset+12*count;pools.append(tuple(struct.iter_unpack('<3f',payload[offset:end])));offset=end
    if len(payload)-offset!=24*sum(data['counts']):raise ValueError('Invalid Flower display cache length')
    points,normals=pools;records=iter(struct.iter_unpack('<IIIIii',payload[offset:]));rows=[];axes=[];panels=profile.structure()[2]
    for home,count in enumerate(data['counts']):
        row=[];cut_ids=[]
        for _ in range(count):
            a,b,c,n,slot,axis=next(records)
            if slot<-1 or slot>=len(panels) or slot>=0 and panels[slot][0]!=home:
                raise ValueError('Invalid Flower display field owner')
            if (slot>=0 and axis!=-1) or (slot<0 and axis not in range(20)):
                raise ValueError('Invalid Flower display cut')
            row.append(((points[a],points[b],points[c]),normals[n],slot))
            cut_ids.append(axis)
        rows.append(tuple(row));axes.append(tuple(cut_ids))
    return tuple(rows),tuple(axes)


def surfaces():return skin_data()[0]


@lru_cache(maxsize=2)
def outer_surfaces(profile=None):
    masks,regions,panels=(structure() if profile is None else profile.structure());result=[[] for _ in masks]
    for slot,(home,face,p) in enumerate(panels):
        result[home].extend((t,CUBE[face],slot) for t in triangulate(p,CUBE[face]))
    return tuple(map(tuple,result))


class FlowerCopterView(TwinsView):
    home_surfaces=staticmethod(surfaces)
    skin=staticmethod(skin_data)
    outer_skin=staticmethod(outer_surfaces)

    def _surfaces(self,cube):
        from cube.appearance import transform_frame
        from cube.flower_copter import frame_action
        shell_only=self._move is None and self.piece_filter is None
        turn_axis=self._move.axis if self._move is not None and self.piece_filter is None else None
        try:cube.aligned_permutation()
        except ValueError:
            shell_only=False;turn_axis=None
        cache=getattr(self,'_flower_placed',None)
        cache_key=cube.frames,shell_only,self._move.axis if self._move is not None else None
        if cache is None or cache[0]!=cache_key:
            placed=[]
            from renderer.cad_copter_visibility import visible_cuts
            # Butterflower has its own radius-one arrangement and renderer;
            # this topology belongs only to the Drawing1 material.
            exposed=None
            if cube.puzzle_kind=='lanlan_flower_copter' and not shell_only:
                moving=cube.selection(self._move.axis) if self._move is not None else ()
                exposed=visible_cuts(cube,'flower',moving)
            for home,parts in enumerate(self.outer_skin() if shell_only else self.home_surfaces()):
                frame=cube.frames[home]
                try:axes=frame_action(frame)[0] if turn_axis is not None else None
                except ValueError:
                    # Exposed plastic remains part of a jumbled rigid piece.
                    # It cannot be indexed by a canonical cube rotation.
                    axes=None
                cut_ids=self.skin()[1][home] if turn_axis is not None or exposed is not None else ()
                for i,(triangle,normal,slot) in enumerate(parts):
                    if slot<0 and exposed is not None and cut_ids[i] not in exposed[home]:continue
                    # Only the active cut separates the two moving rigid
                    # aggregates. Their other interior contacts stay hidden.
                    if slot<0 and exposed is None and turn_axis is not None and axes is not None and axes[cut_ids[i]]!=turn_axis:continue
                    placed.append((tuple(transform_frame(frame,p) for p in triangle),transform_frame(frame,normal),slot,home))
            self._flower_placed=cache_key,tuple(placed)
        return tuple((poly,normal,cube.paints[slot] if slot>=0 and cube.paints[slot]>=0 else -2 if slot>=0 else -1,
                      slot if slot>=0 else None,0,home,1) for poly,normal,slot,home in self._flower_placed[1]
                     if self.piece_filter is None or home==self.piece_filter)


class FlowerCopterTwistView(FlowerCopterView,CopterTwistView):
    edge_amount=180.
    corner_amount=120.
    def amount_for_axis(self,axis):return self.edge_amount if axis<12 else self.corner_amount
