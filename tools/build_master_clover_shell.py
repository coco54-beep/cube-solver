"""Offline regular shell: split petals, bonded corner/centre observations.

The extra arc is reconstructed from photographs, not a measured internal
cut surface. This asset deliberately certifies only closed half-turns.
"""
import sys,json,zlib,math
from pathlib import Path
from itertools import product
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import split
from cube.polyhedral import CUBE,EDGE_AXES,Spec,scale,dot,cross,unit,mean
from cube.curved_partition import SphereCut,shell


def build():
    cuts=tuple(SphereCut(tuple(round(v) for v in scale(n,math.sqrt(2))),1.) for n in EDGE_AXES)
    base=shell(Spec('clover-reference',3,CUBE,EDGE_AXES,(),360),cuts)
    corners=tuple(product((-1.,1.),repeat=3));panels=[];roles=[];wing=20
    def parts(shape):
        return [shape] if shape.geom_type=='Polygon' else list(shape.geoms)
    for mask,face,poly in base:
        n=CUBE[face];u=next(v for v in CUBE if dot(n,v)==0);v=cross(n,u)
        shape=Polygon([(dot(p,u),dot(p,v)) for p in poly])
        def emit(h,s,kind,axes):
            points=list(s.exterior.coords)[:-1]
            if not s.exterior.is_ccw:points.reverse()
            xyz=tuple(tuple(n[j]+x*u[j]+y*v[j] for j in range(3)) for x,y in points)
            panels.append((h,face,xyz));roles.append(dict(kind=kind,axes=axes))
        axes=[i for i in range(12) if mask&(1<<i)]
        if len(axes)==1:emit(8+axes[0],shape,'edge',axes);continue
        if len(axes)!=2:raise ValueError('Unexpected reference petal')
        hub=shape.centroid;signs=(1 if hub.x>0 else -1,1 if hub.y>0 else -1)
        corner=tuple(n[j]+signs[0]*u[j]+signs[1]*v[j] for j in range(3))
        owner=corners.index(corner)
        disc=Point(signs[0]*.5,signs[1]*.5).buffer(.5,quad_segs=48)
        inner=shape.intersection(disc)
        line=LineString([(signs[0]*-2,signs[1]*-2),(signs[0]*2,signs[1]*2)])
        wings=parts(split(inner,line));ends=parts(shape.difference(disc))
        if len(wings)!=2 or len(ends)!=2:raise ValueError('A petal must have two wings and two bonded end patches')
        for end in sorted(ends,key=lambda s:s.centroid.x*signs[0]+s.centroid.y*signs[1]):
            emit(owner,end,'bonded',axes)
        for piece in sorted(wings,key=lambda s:s.centroid.x*signs[0]-s.centroid.y*signs[1]):
            emit(wing,piece,'wing',axes);wing+=1
    assert len(panels)==120 and wing==68
    data=dict(version=1,profile='photo-regular-shell-v1',arc_radius=.5,corners=corners,panels=panels,roles=roles,
              limitation='Closed half-turn model; internal partial-turn surfaces are not certified.')
    target=Path(__file__).resolve().parents[1]/'cube/data/master_clover_shell.bin'
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print(target,len(panels),wing,target.stat().st_size)


if __name__=='__main__':build()
