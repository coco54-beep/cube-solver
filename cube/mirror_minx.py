"""Offset-shell Kilominx and Megaminx, with sixty rigid body frames.

Outer face heights vary while mechanical cuts stay fixed. The two-order
model partitions whole faces between corners; it does not leave holes where
the ordinary Megaminx edges and centres would have been.
"""
from functools import lru_cache
import math
from cube.mastermorphix import IDENTITY,transform
from cube.mirror_pyraminx import MirrorPyraminxCube
from cube.mirror_tower import frame_key,multiply,_clip_solid
from cube.polyhedral import (geometry,body,rotate,add,scale,dot,key,Sticker,Geometry)

OFFSET=(.113,-.079,.047)


@lru_cache(maxsize=1)
def frames():
    g=geometry('megaminx',3);found=[IDENTITY];seen={frame_key(IDENTITY)}
    for frame in found:
        for axis in g.spec.axes[:2]:
            nxt=tuple(rotate(v,axis,2*math.pi/5) for v in frame)
            k=frame_key(nxt)
            if k not in seen:seen.add(k);found.append(nxt)
    if len(found)!=60:raise ValueError('Minx body must have sixty proper rotations')
    return tuple(found)


@lru_cache(maxsize=4096)
def placements(n,home,position):
    g=geometry('megaminx',n)
    return tuple(f for f in frames() if sum((a-b)**2 for a,b in
                 zip(transform(f,g.centres[home]),g.centres[position]))<1e-9)


@lru_cache(maxsize=124)
def piece_faces(n,home):
    g=geometry('megaminx',n)
    polygons=[(tuple(add(p,OFFSET) for p in face),0) for face in body(g.spec.normals)]
    centre=g.centres[home]
    if n==2:
        # Equal-radius corner centres give a symmetric Voronoi partition.
        # Its exterior consists of the three quadrilateral corner sectors.
        for other in g.centres:
            delta=add(other,scale(centre,-1))
            if dot(delta,delta)<1e-12:continue
            bound=(dot(other,other)-dot(centre,centre))/2
            polygons=_clip_solid(polygons,delta,bound)
    else:
        for axis in g.spec.axes:
            value=dot(axis,centre)
            below=[c for c in g.spec.cuts if c<value-1e-8]
            above=[c for c in g.spec.cuts if c>value+1e-8]
            if below:polygons=_clip_solid(polygons,scale(axis,-1),-max(below))
            if above:polygons=_clip_solid(polygons,axis,min(above))
    return tuple(polygons)


@lru_cache(maxsize=8192)
def appearance(n,home,frame):
    return tuple(sorted(tuple(sorted(key(transform(frame,p)) for p in poly))
                        for poly,color in piece_faces(n,home) if color>=0))


@lru_cache(maxsize=2)
def marker_system(n):
    g=geometry('megaminx',n);pending=set(range(len(g.pieces)));points=[];orbit=0
    while pending:
        home=min(pending);members=set()
        for frame in frames():
            point=transform(frame,g.centres[home])
            position=min(range(len(g.pieces)),key=lambda i:sum((a-b)**2 for a,b in zip(g.centres[i],point)))
            if sum((a-b)**2 for a,b in zip(g.centres[position],point))>1e-9:
                raise ValueError('Minx piece orbit is not closed')
            points.append((orbit,position,frame));members.add(position)
        if not members<=pending:raise ValueError('Overlapping minx body orbits')
        pending-=members;orbit+=1
    index={(o,frame_key(f)):i for i,(o,p,f) in enumerate(points)}
    permutations=[]
    for axis,layers in enumerate(g.layers):
        turn=tuple(rotate(v,g.spec.axes[axis],2*math.pi/5) for v in IDENTITY)
        permutations.append(tuple(tuple(index[o,frame_key(multiply(turn,f))] if p in layer else i
                                   for i,(o,p,f) in enumerate(points)) for layer in layers))
    stickers=tuple(Sticker(p,i,()) for i,(o,p,f) in enumerate(points))
    pieces=tuple(tuple(i for i,(o,pos,f) in enumerate(points) if pos==p) for p in range(len(g.pieces)))
    return tuple(points),index,Geometry(g.spec,stickers,pieces,g.centres,tuple(permutations),g.layers)


class MirrorMinxCube(MirrorPyraminxCube):
    mechanism_kind='megaminx'
    supported_orders=(2,3)
    color_count=1

    @property
    def puzzle_kind(self):return 'mirror_kilominx' if self.n==2 else 'mirror_megaminx'

    def rotation_frames(self):return frames()
    def marker_model(self):return marker_system(self.n)
    def placement_frames(self,home,position):return placements(self.n,home,position)
    def piece_faces(self,home):return piece_faces(self.n,home)

    def is_solved(self):
        return (set(self.pieces)==set(range(len(self.geometry.pieces))) and all(
            appearance(self.n,p.home,p.frame)==appearance(self.n,position,IDENTITY)
            for position,p in self.pieces.items()))
