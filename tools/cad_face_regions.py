"""Offline planar CAD regions, splitting analytic curves before tessellation.

CAD segments are data. Region IDs describe face patches, not rigid cubies.
No CAD parser or Shapely dependency is introduced into the application.
"""
import math
from dataclasses import dataclass,replace

# DWG round-trips leave central trimmed-arc endpoints about 4e-8 off the
# adjoining circle in normalized coordinates. Weld within 2e-7 (one
# millionth of the drawing's side-ten unit), preserving all source curves.
EPS=2e-7


def sub(a,b):return (a[0]-b[0],a[1]-b[1])
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def dot(a,b):return a[0]*b[0]+a[1]*b[1]


@dataclass(frozen=True)
class Curve:
    kind:str
    a:tuple
    b:tuple=()
    radius:float=0.
    start:float=0.
    span:float=0.
    handle:str=''

    def point(self,t):
        if self.kind=='line':return tuple(x+(y-x)*t for x,y in zip(self.a,self.b))
        angle=self.start+self.span*t
        return self.a[0]+self.radius*math.cos(angle),self.a[1]+self.radius*math.sin(angle)

    def parameter(self,p):
        if self.kind=='line':
            delta=sub(self.b,self.a);t=dot(sub(p,self.a),delta)/dot(delta,delta)
            if -EPS<=t<=1+EPS and abs(cross(delta,sub(p,self.a)))<=EPS:return min(1.,max(0.,t))
        else:
            delta=sub(p,self.a)
            if abs(math.hypot(*delta)-self.radius)>EPS:return None
            angle=(math.atan2(delta[1],delta[0])-self.start)%math.tau
            if angle>math.tau-EPS:angle=0.
            if angle<=self.span+EPS:return min(1.,max(0.,angle/self.span))
        return None


def curves_from_entities(entities,width=10.):
    def point(p):return tuple((float(v)-width/2)/(width/2) for v in p[:2])
    curves=[]
    for row in entities:
        kind=row['type'];handle=row['handle']
        if kind=='ARC':
            start=math.radians(row['start_angle']);span=math.radians((row['end_angle']-row['start_angle'])%360)
            curves.append(Curve('arc',point(row['center']),radius=row['radius']/(width/2),start=start,span=span,handle=handle))
        elif kind=='LINE':curves.append(Curve('line',point(row['start']),point(row['end']),handle=handle))
        elif kind=='LWPOLYLINE':
            vertices=tuple(point(p) for p in row['points'])
            pairs=zip(vertices,vertices[1:]+vertices[:1] if row['closed'] else vertices[1:])
            curves.extend(Curve('line',a,b,handle=handle) for a,b in pairs)
    return tuple(curves)


def intersections(a,b):
    if a.kind=='line' and b.kind=='line':
        u=sub(a.b,a.a);v=sub(b.b,b.a);den=cross(u,v)
        if abs(den)<1e-12:return tuple(p for p in (a.a,a.b,b.a,b.b) if a.parameter(p) is not None and b.parameter(p) is not None)
        t=cross(sub(b.a,a.a),v)/den
        candidates=(a.point(t),)
    elif a.kind=='line' or b.kind=='line':
        if b.kind=='line':a,b=b,a
        u=sub(a.b,a.a);q=sub(a.a,b.a);aa=dot(u,u);bb=2*dot(u,q);cc=dot(q,q)-b.radius*b.radius
        disc=bb*bb-4*aa*cc
        if disc<-1e-10:return ()
        candidates=tuple(a.point((-bb+s*math.sqrt(max(0.,disc)))/(2*aa)) for s in (-1,1))
    else:
        delta=sub(b.a,a.a);d=math.hypot(*delta)
        if d<1e-12:return tuple(p for p in (a.point(0),a.point(1),b.point(0),b.point(1)) if a.parameter(p) is not None and b.parameter(p) is not None)
        if d>a.radius+b.radius+EPS or d<abs(a.radius-b.radius)-EPS:return ()
        t=(a.radius*a.radius-b.radius*b.radius+d*d)/(2*d);h2=a.radius*a.radius-t*t
        if h2<-1e-10:return ()
        u=delta[0]/d,delta[1]/d;h=math.sqrt(max(0.,h2))
        candidates=tuple((a.a[0]+t*u[0]-s*h*u[1],a.a[1]+t*u[1]+s*h*u[0]) for s in (-1,1))
    return tuple(p for p in candidates if a.parameter(p) is not None and b.parameter(p) is not None)


def with_central_radius(curves,radius,width=10.):
    """Adjust four trimmed centre arcs together, in original drawing units.

    Keep their end contacts on the neighbouring source arcs. This is an
    alternative preview geometry, never a modification of the source CAD.
    """
    if not math.isfinite(radius) or not 0<radius<width/2:
        raise ValueError('Central radius must be positive and smaller than half the face width')
    central=tuple(c for c in curves if c.kind=='arc' and math.hypot(*c.a)<EPS)
    if len(central)!=4:raise ValueError('Expected four central trimmed arcs')
    result=[]
    for curve in curves:
        if curve not in central:
            result.append(curve);continue
        circle=replace(curve,radius=radius/(width/2),start=0.,span=math.tau)
        endpoints=[]
        for t in (0.,1.):
            old=curve.point(t)
            neighbours=[c for c in curves if c.kind=='arc' and c not in central and c.parameter(old) is not None]
            if len(neighbours)!=1:raise ValueError('Central arc endpoint has an ambiguous source contact')
            points=intersections(circle,neighbours[0])
            if not points:raise ValueError('Proposed radius no longer meets the adjoining arc')
            endpoints.append(min(points,key=lambda p:math.hypot(*sub(p,old))))
        angles=[math.atan2(p[1],p[0])%math.tau for p in endpoints]
        span=(angles[1]-angles[0])%math.tau
        if not 0<span<math.pi/2:raise ValueError('Proposed radius changes the central arc topology')
        result.append(replace(circle,start=angles[0],span=span))
    return tuple(result)


def split_curves(curves,step_degrees=1.):
    times=[{0.,1.} for _ in curves]
    for i,a in enumerate(curves):
        for j,b in enumerate(curves[:i]):
            for p in intersections(a,b):times[i].add(a.parameter(p));times[j].add(b.parameter(p))
    paths=[];nodes=[]
    def node(p):
        for q in nodes:
            if math.hypot(*sub(p,q))<=EPS:return q
        nodes.append(p);return p
    for curve,values in zip(curves,times):
        ordered=[]
        for t in sorted(values):
            if not ordered or t-ordered[-1]>1e-9:ordered.append(t)
        for lo,hi in zip(ordered,ordered[1:]):
            count=1 if curve.kind=='line' else max(1,math.ceil(math.degrees(curve.span*(hi-lo))/step_degrees))
            points=tuple(tuple(round(v,8) for v in curve.point(lo+(hi-lo)*i/count)) for i in range(count+1))
            points=(node(points[0]),)+points[1:-1]+(node(points[-1]),)
            if points[0]!=points[-1]:paths.append((curve.handle,points))
    return tuple(paths)


def face_regions(curves,step_degrees=1.):
    from shapely.geometry import LineString,box
    from shapely.ops import unary_union,polygonize
    paths=split_curves(curves,step_degrees)
    regions=tuple(p for p in polygonize(unary_union([LineString(points) for handle,points in paths])) if p.area>1e-10)
    regions=tuple(sorted(regions,key=lambda p:(-round(p.representative_point().y,6),round(p.representative_point().x,6))))
    if not regions or any(not p.is_valid or p.interiors for p in regions):raise ValueError('CAD regions are open or have unsupported holes')
    if abs(sum(p.area for p in regions)-4)>1e-7 or unary_union(regions).symmetric_difference(box(-1,-1,1,1)).area>1e-7:
        raise ValueError('CAD regions do not cover the complete face')
    return regions,paths
