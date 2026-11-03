"""Distance bounds for bounded regions cut by planes and spheres.

A region retains both sides of each curved cut as inequalities, including
its uncoloured interior. A new spherical turn must contain the WHOLE region
or miss its interior. Surface tessellation and a piece centroid cannot
establish that. This module is an analytic geometry kernel, not a claim
about the rails or hidden filler parts of a manufactured puzzle.

Squared distance extrema occur at an interior stationary point, a face
stationary point, a boundary-circle/line stationary point, or a vertex.
The arrangement enumerates these strata instead of sampling display arcs.
"""
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations,product
import math
from cube.polyhedral import add,scale,dot,cross,unit,key
from cube.curved_partition import SphereCut,radial_remainder

TOL=2e-8


def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def norm2(p):return dot(p,p)


def residual(surface,point):
    return (dot(surface.normal,point)-surface.bound if isinstance(surface,Plane)
            else norm2(sub(point,surface.centre))-surface.radius*surface.radius)


def _strict_polyhedron(normals,bounds):
    """Small-dimensional strict linear feasibility, no optimisation library.

    The closest point of a nonempty closed polyhedron has at most three
    independent active planes. Shift the planes by the numeric tolerance,
    then enumerate those candidates.
    """
    limits=tuple(b-1e-9 for b in bounds)
    def feasible(p):return all(dot(n,p)<=b+1e-11 for n,b in zip(normals,limits))
    if feasible((0.,0.,0.)):return True
    for i,n in enumerate(normals):
        if feasible(scale(n,limits[i])):return True
    for i,j in combinations(range(len(normals)),2):
        a,b=normals[i],normals[j];cosine=dot(a,b);det=1-cosine*cosine
        if det<1e-16:continue
        x=(limits[i]-cosine*limits[j])/det;y=(limits[j]-cosine*limits[i])/det
        if feasible(add(scale(a,x),scale(b,y))):return True
    for i,j,k in combinations(range(len(normals)),3):
        a,b,c=(normals[t] for t in (i,j,k));det=dot(a,cross(b,c))
        if abs(det)<1e-12:continue
        p=scale(add(add(scale(cross(b,c),limits[i]),scale(cross(c,a),limits[j])),
                    scale(cross(a,b),limits[k])),1/det)
        if feasible(p):return True
    return False


def _unbounded_cone(normals):
    """Whether n.dot(direction)<=0 has a nonzero recession direction."""
    seeds=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    directions=list(seeds)
    directions.extend(cross(a,b) for a,b in combinations(normals,2))
    directions.extend(cross(a,b) for a in normals for b in seeds)
    for raw in directions:
        if norm2(raw)<1e-20:continue
        d=unit(raw)
        for sign in (-1,1):
            if all(sign*dot(n,d)<=1e-10 for n in normals):return True
    return False


@dataclass(frozen=True)
class Plane:
    normal:tuple
    bound:float


@dataclass(frozen=True)
class Circle:
    centre:tuple
    normal:tuple
    radius:float


@dataclass(frozen=True)
class Line:
    centre:tuple
    direction:tuple


def radical(a,b):
    """Plane containing the intersection of two nonconcentric spheres."""
    delta=sub(b.centre,a.centre)
    return Plane(scale(delta,2),norm2(b.centre)-b.radius*b.radius-norm2(a.centre)+a.radius*a.radius)


def line_of_planes(a,b):
    direction=cross(a.normal,b.normal);d2=norm2(direction)
    if d2<1e-20:return None
    centre=scale(add(scale(cross(b.normal,direction),a.bound),
                     scale(cross(direction,a.normal),b.bound)),1/d2)
    return Line(centre,scale(direction,1/math.sqrt(d2)))


def pair_curve(a,b):
    if isinstance(a,Plane) and isinstance(b,Plane):return line_of_planes(a,b)
    if isinstance(a,Plane):a,b=b,a
    if isinstance(b,SphereCut):b=radical(a,b)
    n2=norm2(b.normal)
    if n2<1e-20:return None
    height=(dot(b.normal,a.centre)-b.bound)/math.sqrt(n2)
    r2=radial_remainder(a.radius*a.radius,height*height)
    if r2<-TOL:return None
    normal=scale(b.normal,1/math.sqrt(n2))
    return Circle(sub(a.centre,scale(normal,height)),normal,math.sqrt(max(0.,r2)))


def three_points(surfaces):
    spheres=[s for s in surfaces if isinstance(s,SphereCut)]
    planes=[s for s in surfaces if isinstance(s,Plane)]
    if not spheres:
        a,b,c=planes;det=dot(a.normal,cross(b.normal,c.normal))
        if abs(det)<1e-12:return ()
        point=scale(add(add(scale(cross(b.normal,c.normal),a.bound),
                            scale(cross(c.normal,a.normal),b.bound)),
                        scale(cross(a.normal,b.normal),c.bound)),1/det)
        return (point,)
    sphere=spheres[0];planes.extend(radical(sphere,s) for s in spheres[1:])
    line=line_of_planes(*planes)
    if line is None:return ()
    difference=sub(line.centre,sphere.centre);t=-dot(difference,line.direction)
    radius2=radial_remainder(sphere.radius*sphere.radius,norm2(add(difference,scale(line.direction,t))))
    if radius2<-TOL:return ()
    h=math.sqrt(max(0.,radius2))
    return tuple(add(line.centre,scale(line.direction,t+sign*h)) for sign in (-1,1))


class Arrangement:
    """All cuts plus the bounding convex body (plane interiors <= bound)."""
    def __init__(self,planes,cuts):
        self.planes=tuple(planes);self.cuts=tuple(cuts)
        self.surfaces=self.planes+self.cuts
        if not self.planes:raise ValueError('A spherical region needs a bounded body')
        self.curves=tuple(
            (i,j,curve) for i,j in combinations(range(len(self.surfaces)),2)
            for curve in (pair_curve(self.surfaces[i],self.surfaces[j]),) if curve is not None)
        vertices={}
        for indices in combinations(range(len(self.surfaces)),3):
            for point in three_points(tuple(self.surfaces[i] for i in indices)):
                if all(dot(p.normal,point)<=p.bound+TOL for p in self.planes):
                    vertices.setdefault(tuple(round(x,10) for x in point),point)
        self.vertices=tuple(vertices.values())
        self._regions={}

    def contains(self,mask,point,tolerance=TOL):
        if any(dot(p.normal,point)>p.bound+tolerance for p in self.planes):return False
        for i,s in enumerate(self.cuts):
            distance=residual(s,point)
            if (distance if mask&(1<<i) else -distance)>tolerance:return False
        return True

    def region(self,mask):
        if mask not in self._regions:self._regions[mask]=Region(self,mask)
        return self._regions[mask]

    @lru_cache(maxsize=256)
    def critical_points(self,centre):
        """All possible distance extrema, before selecting a material cell."""
        points=list(self.vertices);points.append(centre)
        for surface in self.surfaces:
            if isinstance(surface,Plane):
                points.append(sub(centre,scale(surface.normal,(dot(surface.normal,centre)-surface.bound)/norm2(surface.normal))))
            else:
                delta=sub(centre,surface.centre);d2=norm2(delta)
                directions=(scale(delta,1/math.sqrt(d2)),) if d2>1e-20 else ((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
                for direction in directions:
                    points.extend(add(surface.centre,scale(direction,sign*surface.radius)) for sign in (-1,1))
        for i,j,curve in self.curves:
            if isinstance(curve,Line):
                points.append(add(curve.centre,scale(curve.direction,dot(sub(centre,curve.centre),curve.direction))))
            else:
                delta=sub(centre,curve.centre)
                radial=sub(delta,scale(curve.normal,dot(delta,curve.normal)));r2=norm2(radial)
                if r2>1e-20:direction=scale(radial,1/math.sqrt(r2))
                else:
                    seed=min(((1.,0.,0.),(0.,1.,0.),(0.,0.,1.)),key=lambda p:abs(dot(p,curve.normal)))
                    direction=unit(cross(curve.normal,seed))
                points.extend(add(curve.centre,scale(direction,sign*curve.radius)) for sign in (-1,1))
        unique={tuple(round(v,11) for v in p):p for p in points
                if all(dot(n.normal,p)<=n.bound+TOL for n in self.planes)}
        return tuple(unique.values())

    @lru_cache(maxsize=1)
    def positive_masks(self):
        """Find hidden as well as visible full-dimensional material regions.

        Every nonempty bounded material cell has a distance maximum among
        these face/edge/vertex candidates. Inversion rejects ghost contacts.
        No voxel grid, exterior colour or guessed piece centre is used.
        """
        masks=set()
        for point in self.critical_points((0.,0.,0.)):
            residuals=tuple(residual(c,point) for c in self.cuts)
            fixed=sum(1<<i for i,d in enumerate(residuals) if d<-TOL)
            touching=tuple(i for i,d in enumerate(residuals) if abs(d)<=TOL)
            for bits in product((0,1),repeat=len(touching)):
                mask=fixed+sum(1<<i for i,b in zip(touching,bits) if b)
                if mask not in masks and self.region(mask).interior_closure(point):masks.add(mask)
        return tuple(sorted(masks))

    @lru_cache(maxsize=128)
    def linear_critical_points(self,normal):
        """Extrema of n.p on every boundary stratum, without mesh sampling."""
        points=list(self.vertices)
        direction=unit(normal)
        for surface in self.surfaces:
            if isinstance(surface,SphereCut):
                points.extend(add(surface.centre,scale(direction,s*surface.radius)) for s in (-1,1))
        for i,j,curve in self.curves:
            if not isinstance(curve,Circle):continue
            radial=sub(direction,scale(curve.normal,dot(direction,curve.normal)))
            if norm2(radial)<1e-20:
                seed=min(((1.,0.,0.),(0.,1.,0.),(0.,0.,1.)),key=lambda p:abs(dot(p,curve.normal)))
                radial=cross(curve.normal,seed)
            radial=unit(radial)
            points.extend(add(curve.centre,scale(radial,s*curve.radius)) for s in (-1,1))
        return tuple({tuple(round(v,11) for v in p):p for p in points
                      if all(dot(n.normal,p)<=n.bound+TOL for n in self.planes)}.values())


class Region:
    def __init__(self,arrangement,mask):
        if type(mask) is not int or mask<0 or mask>=1<<len(arrangement.cuts):
            raise ValueError('Invalid sphere membership')
        self.arrangement=arrangement;self.mask=mask
        self.vertices=tuple(p for p in arrangement.vertices if self.interior_closure(p))

    @lru_cache(maxsize=4096)
    def interior_closure(self,point):
        """Exclude isolated contacts that are not part of the solid closure.

        A closed Boolean inequality can contain a point with no material
        near it, for example where four cuts meet a body face. Spherical
        inversion about this point turns each touching sphere into a plane:
        g.h + sign*|h|² < 0 becomes g.v < -sign, v=h/|h|².
        The point borders material exactly when this strict polyhedron is
        nonempty and unbounded. This also retains genuine tangential cusps,
        which a first-order inward-direction test would incorrectly remove.
        """
        a=self.arrangement
        if not a.contains(self.mask,point):return False
        normals=[];bounds=[]
        for plane in a.planes:
            if abs(dot(plane.normal,point)-plane.bound)>TOL:continue
            length=math.sqrt(norm2(plane.normal))
            normals.append(scale(plane.normal,1/length));bounds.append(0.)
        for i,sphere in enumerate(a.cuts):
            if isinstance(sphere,Plane):
                if abs(residual(sphere,point))>TOL:continue
                sign=1 if self.mask&(1<<i) else -1
                length=math.sqrt(norm2(sphere.normal))
                normals.append(scale(sphere.normal,sign/length));bounds.append(0.)
                continue
            delta=sub(point,sphere.centre)
            if abs(norm2(delta)-sphere.radius*sphere.radius)>TOL:continue
            sign=1 if self.mask&(1<<i) else -1
            gradient=scale(delta,2*sign);length=math.sqrt(norm2(gradient))
            if length<1e-15:return False
            normals.append(scale(gradient,1/length));bounds.append(-sign/length)
        if not normals:return True
        inward=scale(tuple(sum(n[i] for n in normals) for i in range(3)),-1)
        if all(dot(n,inward)<-1e-10 for n in normals):return True
        return _unbounded_cone(normals) and _strict_polyhedron(normals,bounds)

    @lru_cache(maxsize=4096)
    def squared_distances(self,centre):
        """True radial range of a closed Boolean cell, within numeric TOL.

        Enumerate all surfaces even if the cell has no vertices (for example
        a ball wholly inside a box). Vertex-only pruning misses such pieces.
        """
        points=[point for point in self.arrangement.critical_points(centre) if self.interior_closure(point)]
        if not points:raise ValueError('No feasible spherical-cell extremum')
        distances=[norm2(sub(point,centre)) for point in points]
        return min(distances),max(distances)

    def side(self,cut):
        if isinstance(cut,Plane):
            values=[dot(cut.normal,p)-cut.bound for p in self.arrangement.linear_critical_points(tuple(cut.normal))
                    if self.interior_closure(p)]
            if not values:raise ValueError('No feasible spherical-cell extremum')
            if max(values)<=TOL:return 1
            if min(values)>=-TOL:return -1
            return 0
        low,high=self.squared_distances(tuple(cut.centre));r2=cut.radius*cut.radius
        if high<=r2+TOL:return 1
        if low>=r2-TOL:return -1
        return 0
