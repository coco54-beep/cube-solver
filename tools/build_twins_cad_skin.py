"""Offline display mesh of the CAD CSG partition; never used for clearance."""
import sys,math,json,zlib,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.twins_cad_material import structure,data,cuts,group,fingerprint
from cube.spherical_cells import Plane
from cube.polyhedral import CUBE,add,scale,dot,cross,unit,mean,triangulate,clip
from cube.spherical_surfaces import outline


def sphere_face(mask,index):
    sphere=cuts()[index];planes=[(n,1-dot(n,sphere.centre)) for n in CUBE]
    for j,other in enumerate(cuts()):
        if j==index:continue
        if isinstance(other,Plane):normal=other.normal;bound=other.bound-dot(normal,sphere.centre)
        else:
            delta=add(other.centre,scale(sphere.centre,-1));distance=math.sqrt(dot(delta,delta))
            normal=scale(delta,-1/distance);bound=(other.radius**2-sphere.radius**2-distance**2)/(2*distance)
        if not mask&(1<<j):normal=scale(normal,-1);bound=-bound
        planes.append((normal,bound))
    active=[]
    for normal,bound in planes:
        if bound<=-sphere.radius+1e-9:return ()
        if bound<sphere.radius-1e-9:active.append((normal,bound))
    try:boundary=outline(tuple(active),sphere.radius,segments=64)
    except ValueError as error:
        if str(error)=='Spherical panel has no boundary':return ()
        raise
    if len(boundary)<3:return ()
    direction=unit(mean(boundary));seed=min(CUBE,key=lambda n:abs(dot(n,direction)))
    u=unit(cross(direction,seed));v=cross(direction,u);projected={}
    for p in boundary:
        height=dot(p,direction)
        if height<=1e-8:raise ValueError('Twins patch exceeds a hemisphere')
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
            normal=scale(unit(mean(poly)),sign);points=tuple(add(sphere.centre,p) for p in poly)
            result.extend((t,normal) for t in triangulate(points,normal))
    return tuple(result)


def plane_face(mask,index):
    from shapely.geometry import Polygon,Point
    from shapely.ops import triangulate as triangles
    surface=cuts()[index];n=surface.normal
    u=unit(cross(n,min(CUBE,key=lambda p:abs(dot(p,n)))));v=cross(n,u)
    centre=scale(n,surface.bound);poly=tuple(add(centre,add(scale(u,x),scale(v,y))) for x,y in ((-4,-4),(4,-4),(4,4),(-4,4)))
    for normal,bound in [(p,1.) for p in CUBE]+[(c.normal if mask&(1<<i) else scale(c.normal,-1),
                    c.bound if mask&(1<<i) else -c.bound) for i,c in enumerate(cuts()) if i!=index and isinstance(c,Plane)]:
        poly=clip(poly,normal,bound)
        if not poly:return ()
    shape=Polygon([(dot(p,u),dot(p,v)) for p in poly])
    for i,c in enumerate(cuts()):
        if isinstance(c,Plane):continue
        height=dot(c.centre,n)-surface.bound;r2=c.radius**2-height**2
        if r2<=1e-9:
            if mask&(1<<i):return ()
            continue
        disk=Point(dot(c.centre,u),dot(c.centre,v)).buffer(math.sqrt(r2),resolution=90)
        shape=shape.intersection(disk) if mask&(1<<i) else shape.difference(disk)
        if shape.is_empty:return ()
    sign=1 if mask&(1<<index) else -1;normal=scale(n,sign);result=[]
    for t in triangles(shape):
        if t.area<1e-12 or not shape.covers(t):continue
        points=tuple(add(centre,add(scale(u,x),scale(v,y))) for x,y in list(t.exterior.coords)[:3])
        result.extend((q,normal) for q in triangulate(points,normal))
    return tuple(result)


def build():
    groups,regions,panels=structure();owners={g:h for h,g in enumerate(groups)};rows=[[] for _ in groups]
    atoms=set(data()['atoms'])
    for slot,(h,f,p) in enumerate(panels):rows[h].extend((t,CUBE[f],slot,-1) for t in triangulate(p,CUBE[f]))
    for count,mask in enumerate(sorted(atoms)):
        h=owners[group(mask)]
        for i,c in enumerate(cuts()):
            neighbour=mask^(1<<i)
            if neighbour not in atoms or group(neighbour)==group(mask):continue
            parts=plane_face(mask,i) if isinstance(c,Plane) else sphere_face(mask,i)
            rows[h].extend((tuple(scale(p,.99999) for p in t),n,-1,i) for t,n in parts)
        if count%40==0:print('cells',count,'/',len(atoms),flush=True)
    points={};normals={};records=[]
    def index(pool,p,precision):
        p=tuple(round(x,precision) for x in p)
        if p not in pool:pool[p]=len(pool)
        return pool[p]
    for row in rows:
        for t,n,slot,axis in row:records.append(tuple(index(points,p,7) for p in t)+(index(normals,n,6),slot,axis))
    header=json.dumps(dict(version=3,source=fingerprint(),counts=list(map(len,rows)),points=len(points),normals=len(normals)),separators=(',',':')).encode()
    payload=bytearray(struct.pack('<I',len(header))+header)
    for pool in (points,normals):
        for p in pool:payload.extend(struct.pack('<3f',*p))
    for r in records:payload.extend(struct.pack('<IIIIii',*r))
    target=Path('cube/data/twins_cad_skin.bin');target.write_bytes(zlib.compress(payload,9))
    print('triangles',len(records),'bytes',target.stat().st_size,flush=True)


if __name__=='__main__':build()
