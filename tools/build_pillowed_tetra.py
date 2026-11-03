"""Independent Reuleaux tetrahedron mesh; SciPy is an offline tool only.

The body is the intersection of four radius-edge-length balls about the
tetrahedron's vertices. Its chordal mesh approximates the curved housing.
"""
import sys,math,json,zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.spatial import ConvexHull
from cube.polyhedral import TETRA,unit,scale,add,dot,cross,key
from cube.spherical_surfaces import outline
from cube.appearance import ROTATIONS,transform_frame


if __name__=='__main__':
    tips=tuple(scale(n,math.sqrt(3)/2) for n in TETRA);radius=math.sqrt(2)
    centre=tips[0];planes=[]
    for p in tips[1:]:
        delta=add(p,scale(centre,-1));distance=math.sqrt(dot(delta,delta))
        planes.append((scale(delta,-1/distance),-distance/2))
    boundary=outline(tuple(planes),radius,segments=60)
    hub=scale(unit(tuple(sum(p[i] for p in boundary) for i in range(3))),radius)
    seeds=[add(centre,hub)]
    for p in boundary:
        for k in range(1,5):seeds.append(add(centre,scale(unit(add(scale(hub,1-k/4),scale(p,k/4))),radius)))
    points={}
    rotations=[r for r in ROTATIONS if {key(transform_frame(r,p)) for p in tips}=={key(p) for p in tips}]
    for r in rotations:
        for p in seeds:
            q=transform_frame(r,p)
            if any(sum((a-b)**2 for a,b in zip(q,c))>radius*radius+1e-7 for c in tips):raise ValueError('Housing sample leaves ball intersection')
            points[key(q)]=q
    cloud=np.array(tuple(points.values()));hull=ConvexHull(cloud)
    groups={}
    for tri,equation in zip(hull.simplices,hull.equations):
        normal=equation[:3];bound=-equation[3]
        group=tuple(round(float(x),7) for x in (*normal,bound))
        groups.setdefault(group,set()).update(map(int,tri))
    faces=[]
    for plane,indices in groups.items():
        normal=np.array(plane[:3]);vertices=cloud[list(indices)];mean=vertices.mean(axis=0)
        u=vertices[0]-mean;u=u/np.linalg.norm(u);v=np.cross(normal,u)
        vertices=sorted(vertices,key=lambda p:math.atan2(np.dot(p-mean,v),np.dot(p-mean,u)))
        centroid=sum(vertices)/len(vertices)
        color=min(range(4),key=lambda i:abs(float(np.linalg.norm(centroid-tips[i]))-radius))
        faces.append(([list(map(float,p)) for p in vertices],color))
    target=Path('cube/data/pillowed_tetra_shell.bin');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(zlib.compress(json.dumps(dict(version=1,model='four-ball-reuleaux-tetrahedron',faces=faces),separators=(',',':')).encode(),9))
    print('vertices',len(cloud),'facets',len(faces),'bytes',target.stat().st_size)
