"""Shared curved display surface for the Drum and five-axis prism.

The warp commutes with each family's body symmetries, so a completed native
turn lands on the same surface. Sticker fills, seams and picking use this
same map; logical colour and piece IDs remain independent of tessellation.
"""
from functools import lru_cache
import math

from cube.polyhedral import geometry, add, scale, mean, cross, dot, unit
from cube.prism import SIDES, triangular_face_cuts
from cube.war_drum import NORMALS as DRUM_NORMALS


_CAP_TANGENTS = tuple(tuple(unit(add(n, scale(cap, -dot(n, cap))))
                            for i, n in enumerate(DRUM_NORMALS[:4]) if i != j)
                      for j, cap in enumerate(DRUM_NORMALS[4:]))
_PRISM_CORNERS = tuple(scale(n, -2.) for n in SIDES)


def _divisions(n, kind):
    if kind == 'war_drum':
        return 4 if n <= 3 else 3
    return max(4, 8-n)


@lru_cache(maxsize=24000)
def surface_point(point, kind, n=3):
    if kind == 'war_drum':
        radius = math.sqrt(dot(point, point))
        rounded = scale(point, .72+.28*2.05/max(radius, 1e-8))
        # The triangular caps have in-plane rounding. Blend the
        # hexagon bulge into their shared boundary while keeping caps planar.
        # Cap neighbourhoods above projection 1 do not overlap; the smooth
        # weight vanishes before the nearest-cap choice can change.
        cap_id = max(range(4), key=lambda i: dot(point, DRUM_NORMALS[i+4]))
        cap = DRUM_NORMALS[cap_id+4]
        height = dot(point, cap)
        if height <= 1:
            return rounded
        radial = add(point, scale(cap, -height))
        length = math.sqrt(dot(radial, radial))
        factor = (.8+.2*1.55*max(dot(n, radial) for n in _CAP_TANGENTS[cap_id])/length
                  if length > 1e-8 else 1.)
        flat = add(scale(cap, height), scale(radial, factor))
        t = min(1., (height-1)*2)
        weight = t*t*(3-2*t)
        return add(scale(rounded, 1-weight), scale(flat, weight))
    return _prism_surface(point, n)


def _prism_outline_radius(angle):
    direction = (math.cos(angle), math.sin(angle), 0.)
    distances = tuple(dot(v, direction) + math.sqrt(8.+dot(v, direction)**2)
                      for v in _PRISM_CORNERS)
    nearest = min(distances)
    return nearest-math.log(sum(math.exp(-12.*(d-nearest))
                               for d in distances))/12.


def _cap_vertex(point, n):
    """Extend a cut endpoint along its straight cut to the rounded outline."""
    x,y = point[:2]
    projections = tuple(x*s[0]+y*s[1] for s in SIDES)
    boundary = tuple(i for i,q in enumerate(projections) if abs(q-1.) < 1e-7)
    if not boundary:
        return x,y
    if len(boundary)>1:
        angle = math.atan2(y,x)
        radius = _prism_outline_radius(angle)
        return radius*math.cos(angle),radius*math.sin(angle)
    for i,s in enumerate(SIDES):
        if i in boundary or not any(abs(projections[i]-cut)<1e-7
                                   for cut in triangular_face_cuts(n)):
            continue
        tx,ty = -s[1],s[0]
        if x*tx+y*ty < 0:
            tx,ty = -tx,-ty
        # The foot on the cut is inside the rounded body. Find the outward
        # intersection without changing the position of the straight cut.
        lo,hi = -(x*tx+y*ty),3.
        for _ in range(48):
            t = (lo+hi)/2
            px,py = x+t*tx,y+t*ty
            if math.hypot(px,py) < _prism_outline_radius(math.atan2(py,px)):
                lo=t
            else:
                hi=t
        return x+(lo+hi)/2*tx,y+(lo+hi)/2*ty
    raise ValueError('Unclassified prism cap boundary vertex')


@lru_cache(maxsize=4)
def _cap_map(n):
    """Straight internal cut segments plus continuous curved outer segments."""
    g=geometry('pentahedron',n)
    fans=[]
    boundary=[{} for _ in SIDES]
    for sticker in g.stickers:
        if sticker.face != 3:
            continue
        for patch in sticker.patches or (sticker.polygon,):
            mapped=tuple(_cap_vertex(p,n) for p in patch)
            centre=mean(patch)
            target=tuple(sum(p[k] for p in mapped)/len(mapped) for k in range(2))
            for p,q in zip(patch,mapped):
                for i,s in enumerate(SIDES):
                    if abs(dot(s,p)-1.)<1e-7:
                        tangent=(-s[1],s[0])
                        boundary[i][round(p[0]*tangent[0]+p[1]*tangent[1],10)]=q
            for i,b in enumerate(patch):
                j=(i+1)%len(patch)
                c=patch[j]
                outer=any(abs(dot(s,b)-1.)<1e-7 and abs(dot(s,c)-1.)<1e-7
                          for s in SIDES)
                fans.append((centre,b,c,target,mapped[i],mapped[j],outer))
    edges=[]
    for anchors in boundary:
        row=[]
        previous=None
        for location,point in sorted(anchors.items()):
            angle=math.atan2(point[1],point[0])
            if previous is not None:
                angle=previous+(angle-previous+math.pi)%(2*math.pi)-math.pi
            row.append((location,angle))
            previous=angle
        edges.append(tuple(row))
    return tuple(fans),tuple(edges)


def _prism_boundary(point,n):
    _,edges=_cap_map(n)
    side=max(range(3),key=lambda i:dot(SIDES[i],point))
    s=SIDES[side]
    location=point[0]*-s[1]+point[1]*s[0]
    row=edges[side]
    angle=row[-1][1]
    for (a,aa),(b,ba) in zip(row,row[1:]):
        if location<=b+1e-8:
            fraction=max(0.,min(1.,(location-a)/(b-a)))
            angle=aa+(ba-aa)*fraction
            break
    radius=_prism_outline_radius(angle)
    return radius*math.cos(angle),radius*math.sin(angle)


def _prism_cap_point(point,n):
    support=max(dot(s,point) for s in SIDES)
    if support>=1.-1e-8:
        return _prism_boundary((point[0]/support,point[1]/support,0.),n)
    x,y=point[:2]
    for a,b,c,ta,tb,tc,outer in _cap_map(n)[0]:
        bx,by,cx,cy=b[0]-a[0],b[1]-a[1],c[0]-a[0],c[1]-a[1]
        determinant=bx*cy-by*cx
        if abs(determinant)<1e-12:
            continue
        u=((x-a[0])*cy-(y-a[1])*cx)/determinant
        v=(bx*(y-a[1])-by*(x-a[0]))/determinant
        if u < -1e-7 or v < -1e-7 or u+v > 1.+1e-7:
            continue
        mapped=tuple((1.-u-v)*ta[k]+u*tb[k]+v*tc[k] for k in range(2))
        if outer and u+v>1e-8:
            t=u+v
            edge=tuple((u*b[k]+v*c[k])/t for k in range(3))
            curved=_prism_boundary(edge,n)
            linear=tuple((u*tb[k]+v*tc[k])/t for k in range(2))
            mapped=tuple(mapped[k]+t*t*(curved[k]-linear[k]) for k in range(2))
        return mapped
    raise ValueError('Prism cap point outside its display partition')


def _prism_surface(point,n):
    """Keep triangle cuts straight and share their rounded rim with the sides."""
    x,y=_prism_cap_point(point,n)
    z=point[2]
    bulge=1.+.075*(1.-min(1.,z*z))
    return x*bulge,y*bulge,z


@lru_cache(maxsize=24000)
def _surface_normal(point, normal, kind, n):
    tangent = unit(cross(normal, (0., 1., 0.) if abs(normal[1]) < .9 else (1., 0., 0.)))
    bitangent = cross(normal, tangent)
    eps = 1e-5
    du = add(surface_point(add(point, scale(tangent, eps)), kind, n),
             scale(surface_point(add(point, scale(tangent, -eps)), kind, n), -1))
    dv = add(surface_point(add(point, scale(bitangent, eps)), kind, n),
             scale(surface_point(add(point, scale(bitangent, -eps)), kind, n), -1))
    result = unit(cross(du, dv))
    return result if dot(result, normal) > 0 else scale(result, -1)


@lru_cache(maxsize=4)
def curved_skin(n, kind):
    g = geometry(kind, n)
    divisions = _divisions(n, kind)
    result = []
    for sticker in g.stickers:
        facets = []
        face_normal = g.spec.normals[sticker.face]
        for patch in sticker.patches or (sticker.polygon,):
            a = mean(patch)
            for b, c in zip(patch, patch[1:]+patch[:1]):
                def point(i, j):
                    return tuple(((divisions-i-j)*a[k]+i*b[k]+j*c[k])/divisions
                                 for k in range(3))
                for i in range(divisions):
                    for j in range(divisions-i):
                        triangles = [(point(i, j), point(i+1, j), point(i, j+1))]
                        if i+j < divisions-1:
                            triangles.append((point(i+1, j), point(i+1, j+1), point(i, j+1)))
                        for original in triangles:
                            points = tuple(surface_point(p, kind, n) for p in original)
                            normal = cross(add(points[1], scale(points[0], -1)),
                                           add(points[2], scale(points[0], -1)))
                            if dot(normal, normal) < 1e-16:
                                continue
                            normal = unit(normal)
                            if dot(normal, face_normal) < 0:
                                normal = scale(normal, -1)
                            vertex_normals = ((face_normal,)*3
                                              if kind=='pentahedron' and sticker.face>=3 else
                                              tuple(_surface_normal(p, face_normal, kind, n)
                                                    for p in original))
                            facets.append((points, normal, vertex_normals))
        result.append(tuple(facets))
    return tuple(result)


@lru_cache(maxsize=12000)
def curved_edge(a, b, n, kind):
    divisions = _divisions(n, kind)
    return tuple(surface_point(tuple(a[k]+(b[k]-a[k])*i/divisions for k in range(3)), kind, n)
                 for i in range(divisions+1))
