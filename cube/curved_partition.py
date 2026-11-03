"""Analytic circle arrangements on a polyhedral shell.

Each sphere/face intersection is split at its actual intersections. Adjacent
panels share the same sampled arcs; piece identities come from cut membership,
never a colour, a guessed centroid or a decorative line.
"""
from dataclasses import dataclass
import math
from cube.polyhedral import add,scale,dot,cross,unit,mean

TOL=1e-9


@dataclass(frozen=True)
class SphereCut:
    centre: tuple
    radius: float


def _cross(a,b):return a[0]*b[1]-a[1]*b[0]
def _sub(a,b):return (a[0]-b[0],a[1]-b[1])
def _point_key(p):return tuple(round(x,8) for x in p)


def arc_steps(angle,segments=180):
    # Symmetric descriptions of one shared arc can differ by a few ulps.
    # A raw ceil would add an extra vertex to only one side at 90/180 deg.
    return max(1,math.ceil(angle*segments/math.tau-1e-10))


def radial_remainder(radius2,distance2):
    """Keep roundoff at tangency from creating a tiny positive circle."""
    result=radius2-distance2
    if abs(result)<=64*math.ulp(max(abs(radius2),abs(distance2))):return 0.
    return result


def partition(polygon,normal,cuts,segments=180):
    """Yield (membership mask, outline) for every connected planar panel."""
    origin=mean(polygon);u=unit(add(polygon[1],scale(polygon[0],-1)));v=cross(normal,u)
    def xy(p):
        p=add(p,scale(origin,-1));return dot(p,u),dot(p,v)
    def xyz(p):return add(origin,add(scale(u,p[0]),scale(v,p[1])))
    vertices=tuple(xy(p) for p in polygon)
    def inside(p):
        return all(_cross(_sub(b,a),_sub(p,a))>=-TOL
                   for a,b in zip(vertices,vertices[1:]+vertices[:1]))
    circles=[]
    for bit,cut in enumerate(cuts):
        height=dot(add(cut.centre,scale(origin,-1)),normal)
        r2=cut.radius**2-height**2
        if r2>TOL:
            centre=xy(cut.centre);radius=math.sqrt(r2)
            # Different 3D cuts can have exactly the same trace on a face.
            # Keep one geometric arc; mask() still evaluates every cut bit.
            if not any(math.dist(centre,c)<TOL and abs(radius-r)<TOL for _,c,r in circles):
                circles.append((bit,centre,radius))
    def mask(p):
        world=xyz(p)
        return sum(1<<i for i,c in enumerate(cuts)
                   if dot(add(world,scale(c.centre,-1)),add(world,scale(c.centre,-1)))<c.radius**2)
    circle_angles=[[] for _ in circles];edge_times=[[0.,1.] for _ in vertices]
    for i,(_,a,ra) in enumerate(circles):
        for j,(_,b,rb) in enumerate(circles[:i]):
            delta=_sub(b,a);distance=math.hypot(*delta)
            if distance<TOL or distance>ra+rb+TOL or distance<abs(ra-rb)-TOL:continue
            t=(ra*ra-rb*rb+distance*distance)/(2*distance)
            h2=radial_remainder(ra*ra,t*t)
            if h2<-TOL:continue
            h=math.sqrt(max(0.,h2));dx,dy=(x/distance for x in delta)
            for sign in (-1,1):
                p=(a[0]+t*dx-sign*h*dy,a[1]+t*dy+sign*h*dx)
                if inside(p):
                    circle_angles[i].append(math.atan2(p[1]-a[1],p[0]-a[0]))
                    circle_angles[j].append(math.atan2(p[1]-b[1],p[0]-b[0]))
        for j,(start,end) in enumerate(zip(vertices,vertices[1:]+vertices[:1])):
            d=_sub(end,start);q=_sub(start,a);aa=sum(x*x for x in d)
            bb=2*sum(x*y for x,y in zip(d,q));cc=sum(x*x for x in q)-ra*ra
            discriminant=radial_remainder(bb*bb,4*aa*cc)
            if discriminant<-TOL:continue
            for sign in (-1,1):
                t=(-bb+sign*math.sqrt(max(0.,discriminant)))/(2*aa)
                if -TOL<=t<=1+TOL:
                    t=min(1.,max(0.,t));p=(start[0]+t*d[0],start[1]+t*d[1])
                    edge_times[j].append(t)
                    circle_angles[i].append(math.atan2(p[1]-a[1],p[0]-a[0]))
    def unique(values,cyclic=False):
        result=[]
        for t in sorted(t%math.tau if cyclic else t for t in values):
            if not result or t-result[-1]>TOL:result.append(t)
        if cyclic and len(result)>1 and result[0]+math.tau-result[-1]<TOL:result.pop()
        return result
    edges=[]
    def emit(points,signature):
        if _point_key(points[0])!=_point_key(points[-1]):
            edges.append((signature,tuple(points)))
    for j,(start,end) in enumerate(zip(vertices,vertices[1:]+vertices[:1])):
        times=unique(edge_times[j]);d=_sub(end,start);length=math.hypot(*d)
        for lo,hi in zip(times,times[1:]):
            a=(start[0]+lo*d[0],start[1]+lo*d[1]);b=(start[0]+hi*d[0],start[1]+hi*d[1])
            mid=((a[0]+b[0])/2-d[1]*1e-7/length,(a[1]+b[1])/2+d[0]*1e-7/length)
            emit((a,b),mask(mid))
    for j,(bit,c,r) in enumerate(circles):
        angles=unique(circle_angles[j],True)
        if not angles:angles=[0.,math.pi]
        if len(angles)==1:angles.append((angles[0]+math.pi)%math.tau);angles.sort()
        for lo,hi in zip(angles,angles[1:]+[angles[0]+math.tau]):
            theta=(lo+hi)/2;mid=(c[0]+r*math.cos(theta),c[1]+r*math.sin(theta))
            if not inside(mid):continue
            count=arc_steps(hi-lo,segments)
            points=tuple((c[0]+r*math.cos(lo+(hi-lo)*i/count),
                          c[1]+r*math.sin(lo+(hi-lo)*i/count)) for i in range(count+1))
            inset=(mid[0]-1e-7*math.cos(theta),mid[1]-1e-7*math.sin(theta))
            outset=(mid[0]+1e-7*math.cos(theta),mid[1]+1e-7*math.sin(theta))
            emit(points,mask(inset));emit(tuple(reversed(points)),mask(outset))
    outgoing={}
    for i,(signature,points) in enumerate(edges):
        outgoing.setdefault((signature,_point_key(points[0])),[]).append(i)
    unused=set(range(len(edges)))
    while unused:
        start=min(unused);signature,points=edges[start];outline=[];current=start
        while current in unused:
            unused.remove(current);_,points=edges[current];outline.extend(points[:-1])
            if _point_key(points[-1])==_point_key(edges[start][1][0]):break
            options=[i for i in outgoing.get((signature,_point_key(points[-1])),()) if i in unused]
            if not options:raise ValueError('Curved panel has an open boundary')
            incoming=_sub(points[-2],points[-1]);angle=math.atan2(incoming[1],incoming[0])
            def turn(i):
                p=edges[i][1];d=_sub(p[1],p[0])
                return (math.atan2(d[1],d[0])-angle)%math.tau
            current=max(options,key=turn)
        else:raise ValueError('Curved panel boundary reused an edge')
        if len(outline)<3:continue
        area=sum(_cross(a,b) for a,b in zip(outline,outline[1:]+outline[:1]))/2
        if area>TOL:yield signature,tuple(xyz(p) for p in outline)
        elif area<-TOL:raise ValueError('Curved panel has an unsupported interior hole')


def shell(spec,cuts):
    from cube.polyhedral import body_faces
    return tuple((membership,face,polygon) for face,poly in enumerate(body_faces(spec))
                 for membership,polygon in partition(poly,spec.normals[face],cuts))
