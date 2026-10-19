"""Real surface patches for bandaged, Penrose, Camouflage and Circle cubes.

Every patch retains its mechanical facelet identity for picking. Border masks
describe physical cuts only; tessellation edges and glued seams are invisible.
This module has no UI dependency so geometry can be checked without OpenGL.
"""
import math

from cube.appearance import PENROSE, PENROSE_RGB, kind_for, frame_for
from cube.coordinates import FACE_NORMALS, get_d_maxc

_FACES = (
    ('R', (1,0,0), ((.5,-.5,-.5),(.5,.5,-.5),(.5,.5,.5),(.5,-.5,.5))),
    ('L', (-1,0,0), ((-.5,-.5,.5),(-.5,.5,.5),(-.5,.5,-.5),(-.5,-.5,-.5))),
    ('U', (0,1,0), ((-.5,.5,.5),(.5,.5,.5),(.5,.5,-.5),(-.5,.5,-.5))),
    ('D', (0,-1,0), ((-.5,-.5,-.5),(.5,-.5,-.5),(.5,-.5,.5),(-.5,-.5,.5))),
    ('F', (0,0,1), ((-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5))),
    ('B', (0,0,-1), ((.5,-.5,-.5),(-.5,-.5,-.5),(-.5,.5,-.5),(.5,.5,-.5))),
)
_RGB = {'W':(1.,1.,1.,1.), 'Y':(1.,.87,0.,1.), 'R':(.87,.075,.09,1.),
        'O':(1.,.45,.015,1.), 'B':(.06,.27,.85,1.), 'G':(.015,.66,.23,1.)}
# Three disjoint rounded edges, each joining the same-colour pair of faces.
_ROUND_EDGES = ((0,1,1,1), (0,-1,2,1), (1,-1,2,-1))
_FACE_DATA = {name:(normal,local) for name,normal,local in _FACES}
_OPPOSITE = {'R':'L','L':'R','U':'D','D':'U','F':'B','B':'F'}


def _dot(a,b): return sum(x*y for x,y in zip(a,b))
def _cross(a,b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _transform(frame,p):
    return tuple(sum(frame[j][i]*p[j] for j in range(3)) for i in range(3))
def _inverse(frame,p): return tuple(_dot(axis,p) for axis in frame)


def _bilinear(verts,u,v):
    return tuple((1-u)*(1-v)*verts[0][i]+u*(1-v)*verts[1][i]
                 +u*v*verts[2][i]+(1-u)*v*verts[3][i] for i in range(3))


def _penrose_point(p,half,radius):
    p=list(p)
    for a,sa,b,sb in _ROUND_EDGES:
        pa,pb=sa*p[a],sb*p[b]
        if pa > half-radius-1e-9 and pb > half-radius-1e-9:
            u=max(0.,min(1.,(pa-half+radius)/radius))
            v=max(0.,min(1.,(pb-half+radius)/radius))
            rho=max(u,v)
            if rho<1e-10:continue
            # Map the entire square corner onto a quarter disc. Mapping its
            # interior as well closes the planar end caps of each fillet.
            angle=(v/u)*math.pi/4 if u>=v else math.pi/2-(u/v)*math.pi/4
            p[a]=sa*(half-radius+radius*rho*math.cos(angle))
            p[b]=sb*(half-radius+radius*rho*math.sin(angle))
    return tuple(p)


def _rounded_join(p,q,half):
    for a,sa,b,sb in _ROUND_EDGES:
        if all(abs(sa*r[a]-half)<1e-7 and abs(sb*r[b]-half)<1e-7 for r in (p,q)):
            return True
    return False


def _group_ids(cube):
    # Some presets describe overlapping plates. Their connected union is one
    # rigid piece and must not acquire a false cut at the overlap.
    parent={}
    def find(x):
        parent.setdefault(x,x)
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    for group in getattr(cube,'groups',()):
        members=sorted(group)
        if members:
            root=find(members[0])
            for member in members[1:]: parent[find(member)]=root
    return {home:find(home) for home in parent}


def _cuts(pos,local,d,cube,groups):
    cub=cube.cubies[pos]
    root=groups.get(cub.home)
    edges=[]
    for edge in range(4):
        a,b=local[edge],local[(edge+1)%4]
        tangent=[(a[i]+b[i]) for i in range(3)]
        # Remove the face-normal component: the remaining nonzero component
        # points from this facelet across that edge to its neighbour.
        normal_axis=next(i for i in range(3) if all(abs(v[i]-local[0][i])<1e-9 for v in local))
        tangent[normal_axis]=0
        axis=next(i for i,v in enumerate(tangent) if abs(v)>.5)
        neighbour=list(pos)
        neighbour[axis]+=d*(1 if tangent[axis]>0 else -1)
        other=cube.cubies.get(tuple(neighbour))
        if root is None or other is None or groups.get(other.home)!=root:
            edges.append(edge)
    return tuple(edges)


def build_variant_scene(cube,moving_positions=None,rotation=None,highlight=None):
    # Curves and exposed cut walls are constant throughout a layer animation.
    # Cache one unrotated surface per state; only transform the moving vertices
    # each frame. The key includes stickers, frames and homes, so painting,
    # turns and centre-identity rebuilding cannot reuse stale geometry.
    moving=frozenset(moving_positions) if moving_positions is not None else None
    focus=frozenset(highlight) if highlight is not None else None
    key=(kind_for(cube),cube.n,moving,focus,
         tuple((tuple(pos),tuple(c.home),frame_for(c),tuple(sorted(c.stickers.items())))
               for pos,c in cube.cubies.items()))
    cached=getattr(cube,'_appearance_scene_cache',None)
    if cached is None or cached[0]!=key:
        base=_build_variant_scene(cube,moving,None,focus)
        cube._appearance_scene_cache=(key,base)
    else:
        base=cached[1]
    vertices=list(base[0])
    if moving is not None and rotation is not None:
        for i,(pos,_face,_edges) in enumerate(base[2]):
            if pos in moving:
                for j in range(4):
                    start=i*28+j*7
                    vertices[start:start+3]=rotation.transform(*vertices[start:start+3])
    return vertices,base[1],base[2]


def _build_variant_scene(cube,moving_positions=None,rotation=None,highlight=None):
    kind=kind_for(cube)
    d,maxc=get_d_maxc(cube.n)
    half=maxc+d*.5
    vertices,indices,infos=[],[],[]
    groups=_group_ids(cube) if kind not in PENROSE|{'circle_2'} else {}
    signatures={}

    def shell_point(p):
        return _penrose_point(p,half,.78*d) if kind in PENROSE else p

    def signature(pos,face):
        key=(pos,face)
        if key not in signatures:
            frame=frame_for(cube.cubies[pos])
            _normal,local=_FACE_DATA[face]
            corners=tuple(_inverse(frame,tuple(pos[i]+d*p[i] for i in range(3))) for p in local)
            signatures[key]=frozenset(tuple(round(v,7) for v in _transform(frame,shell_point(_bilinear(corners,u,w))))
                                     for u in (0.,.5,1.) for w in (0.,.5,1.))
        return signatures[key]

    def emit(points,color,pos,face,edges):
        # A stable broad light makes curved surfaces legible without drawing
        # their tessellation mesh. Body colour stays readable in both themes.
        ab=tuple(points[1][i]-points[0][i] for i in range(3))
        ac=tuple(points[2][i]-points[0][i] for i in range(3))
        normal=_cross(ab,ac)
        length=math.sqrt(_dot(normal,normal)) or 1.
        light=max(0.,_dot(normal,(.28,.73,.62))/length)
        shade=.77+.23*light
        rgba=tuple(c*shade for c in color[:3])+(color[3],)
        if highlight is not None and cube.cubies[pos].home not in highlight:
            rgba=tuple(c*.35+.12 for c in rgba[:3])+(rgba[3],)
        if moving_positions is not None and pos in moving_positions and rotation is not None:
            points=tuple(rotation.transform(*p) for p in points)
        vi=len(vertices)//7
        for point in points: vertices.extend((*point,*rgba))
        indices.extend((vi,vi+1,vi+2,vi,vi+2,vi+3))
        infos.append((pos,face,tuple(edges)))

    for pos,cub in cube.cubies.items():
        frame=frame_for(cub)
        for face,normal,local in _FACES:
            axis=next(i for i,v in enumerate(normal) if v)
            outer=pos[axis]==normal[axis]*maxc
            if not outer:
                if kind not in PENROSE:continue
                neighbour=tuple(pos[i]+normal[i]*d for i in range(3))
                same_motion=(moving_positions is None or (pos in moving_positions)==(neighbour in moving_positions))
                if neighbour in cube.cubies and same_motion and signature(pos,face)==signature(neighbour,_OPPOSITE[face]):
                    continue
            face_label=face if outer else None
            raw=cub.stickers.get(normal,'')
            color=(PENROSE_RGB if kind in PENROSE else _RGB).get(raw,(.17,.19,.23,1.))
            if not outer:color=(.045,.05,.055,1.)
            corners=tuple(tuple(pos[i]+d*p[i] for i in range(3)) for p in local)
            home_corners=tuple(_inverse(frame,p) for p in corners)
            if kind=='circle_2':
                # One quarter disc and its surrounding outer corner. These
                # patches share a curved physical cut, not a painted ring.
                tangents=[i for i in range(3) if i!=axis]
                a,b=tangents
                sa=1 if pos[a]>0 else -1
                sb=1 if pos[b]>0 else -1
                radius=half*.64
                origin=[0.,0.,0.];origin[axis]=normal[axis]*half
                def circle_point(r,t):
                    p=list(origin);p[a]=sa*r*math.cos(t);p[b]=sb*r*math.sin(t)
                    return tuple(p)
                for j in range(12):
                    t0=j*math.pi/24;t1=(j+1)*math.pi/24
                    inner0=circle_point(radius,t0);inner1=circle_point(radius,t1)
                    outer0=circle_point(half/max(math.cos(t0),math.sin(t0)),t0)
                    outer1=circle_point(half/max(math.cos(t1),math.sin(t1)),t1)
                    inner_edges=([0] if j==0 else [])+([2] if j==11 else [])
                    # Orient all quads consistently with the outward normal.
                    reverse=(_dot(_cross(tuple(inner0[i]-origin[i] for i in range(3)),
                                         tuple(inner1[i]-origin[i] for i in range(3))),normal)<0)
                    def oriented(points,edges):
                        if not reverse:return points,edges
                        return tuple(reversed(points)),tuple((2-e)%4 for e in edges)
                    points,edges=oriented((tuple(origin),inner0,inner1,tuple(origin)),inner_edges)
                    emit(points,tuple(min(1.,c*1.035) for c in color[:3])+(1.,),pos,face_label,edges)
                    edges=[1,3]+([0] if j==0 else [])+([2] if j==11 else [])
                    points,edges=oriented((inner0,outer0,outer1,inner1),edges)
                    emit(points,color,pos,face_label,edges)
                continue
            if kind in PENROSE:
                radius=.78*d
                # Only curved pieces need subdivision. Flat centre patches
                # keep the ordinary renderer's small surface count.
                curved=any(_penrose_point(p,half,radius)!=p for p in home_corners)
                steps_u=steps_v=1
                cap=False
                if curved:
                    home_normal=_inverse(frame,normal)
                    fixed=next(i for i,v in enumerate(home_normal) if v)
                    affected=[(a,sa,b,sb) for a,sa,b,sb in _ROUND_EDGES
                              if any(sa*p[a]>half-radius+1e-7 and sb*p[b]>half-radius+1e-7 for p in home_corners)]
                    if any(fixed not in (a,b) for a,_sa,b,_sb in affected):
                        cap=True
                    else:
                        a,_sa,b,_sb=affected[0]
                        curve_axis=b if fixed==a else a
                        if abs(home_corners[1][curve_axis]-home_corners[0][curve_axis])>1e-7:
                            steps_u=12
                        else:
                            steps_v=12
                joined={edge for edge in range(4)
                        if _rounded_join(home_corners[edge],home_corners[(edge+1)%4],half)}
                if cap:
                    # End caps are planar convex polygons. A perimeter fan
                    # closes them without a dense interior tessellation.
                    center=_transform(frame,_penrose_point(_bilinear(home_corners,.5,.5),half,radius))
                    for edge in range(4):
                        a,b=home_corners[edge],home_corners[(edge+1)%4]
                        pa,pb=_penrose_point(a,half,radius),_penrose_point(b,half,radius)
                        mid=_penrose_point(tuple((a[i]+b[i])*.5 for i in range(3)),half,radius)
                        bent=any(abs(mid[i]-(pa[i]+pb[i])*.5)>1e-8 for i in range(3))
                        count=12 if bent else 1
                        for j in range(count):
                            endpoints=[]
                            for t in (j/count,(j+1)/count):
                                p=tuple(a[i]*(1-t)+b[i]*t for i in range(3))
                                endpoints.append(_transform(frame,_penrose_point(p,half,radius)))
                            edges=(1,) if outer and edge not in joined else ()
                            emit((center,endpoints[0],endpoints[1],center),color,pos,face_label,edges)
                    continue
                for row in range(steps_v):
                    for col in range(steps_u):
                        u0,u1=col/steps_u,(col+1)/steps_u
                        v0,v1=row/steps_v,(row+1)/steps_v
                        uv=((u0,v0),(u1,v0),(u1,v1),(u0,v1))
                        points=tuple(_transform(frame,_penrose_point(_bilinear(home_corners,u,v),half,radius)) for u,v in uv)
                        edges=[edge for edge,on in enumerate((row==0,col==steps_u-1,row==steps_v-1,col==0))
                               if on and edge not in joined]
                        emit(points,color,pos,face_label,edges if outer else ())
            else:
                emit(corners,color,pos,face,_cuts(pos,local,d,cube,groups))
    return vertices,indices,infos
