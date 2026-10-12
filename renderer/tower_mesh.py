"""Spherical tetrahedral display skin for Tower puzzles.

Reuse the former high-order Mastermorphix shell while retaining Tower sticker
IDs and legal permutations. Geometry is cached and rotated with its layer.
"""
from functools import lru_cache
import math
from cube.mastermorphix import _high_order_point, VERTICES
from cube.polyhedral import geometry, add, scale, mean, cross, dot, unit

STYLE_VERSION='smooth_tower_lighting_v2'


@lru_cache(maxsize=20000)
def tower_point(point):
    return scale(_high_order_point(scale(point,2/math.sqrt(3))),.85)


@lru_cache(maxsize=5)
def tower_skin(n,kind='moyu'):
    g=geometry(kind,n)
    divisions=max(3,8-n)
    result=[]
    for sticker in g.stickers:
        facets=[]
        # Each face belongs to the sphere about the opposite tetrahedron tip.
        # Its analytic normals are shared across sticker/triangle boundaries;
        # flat triangle normals must only be used for visibility, not lighting.
        center=scale(min(VERTICES,key=lambda p:dot(p,g.spec.normals[sticker.face])),.85)
        for patch in sticker.patches or (sticker.polygon,):
            a=mean(patch)
            for b,c in zip(patch,patch[1:]+patch[:1]):
                def point(i,j):
                    p=tuple(((divisions-i-j)*a[k]+i*b[k]+j*c[k])/divisions for k in range(3))
                    return tower_point(p)
                for i in range(divisions):
                    for j in range(divisions-i):
                        triangles=[(point(i,j),point(i+1,j),point(i,j+1))]
                        if i+j<divisions-1:
                            triangles.append((point(i+1,j),point(i+1,j+1),point(i,j+1)))
                        for points in triangles:
                            normal=cross(add(points[1],scale(points[0],-1)),
                                         add(points[2],scale(points[0],-1)))
                            if dot(normal,normal)<1e-16:
                                continue
                            normal=unit(normal)
                            if dot(normal,g.spec.normals[sticker.face])<0:
                                normal=scale(normal,-1)
                            vertex_normals=tuple(unit(add(p,scale(center,-1))) for p in points)
                            facets.append((points,normal,vertex_normals))
        result.append(tuple(facets))
    return tuple(result)


@lru_cache(maxsize=10000)
def tower_edge(a,b,n):
    divisions=max(3,8-n)
    return tuple(tower_point(tuple(a[k]+(b[k]-a[k])*i/divisions for k in range(3)))
                 for i in range(divisions+1))
