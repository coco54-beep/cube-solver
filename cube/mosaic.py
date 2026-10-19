"""Mosaic/Fadi and Tins: two-depth corner turns with fixed corner caps.

Mosaic retains all eight caps; Tins retains four alternating caps. The other
four Tins vertices split into Dino triangles. Twelve paired square centres
and two twelve-piece outer orbits share the Lattice mechanism.
"""
import math

from cube.polyhedral import (Geometry, Sticker, Spec, CUBE, OCTA, TETRA,
                             add, body, dot, geometry, key, mean, rotate, scale,
                             triangulate, unit)


def mosaic_specification(kind, n):
    if (kind, n) not in (('mosaic', 4), ('tins', 5)):
        raise ValueError('Unsupported Mosaic/Tins model')
    return Spec(kind, n, CUBE, OCTA, (1/math.sqrt(3), 2/math.sqrt(3)), 3)


def mosaic_geometry(kind, n):
    spec=mosaic_specification(kind,n)
    source=geometry('dino',4)
    vertices={key(v):v for face in body(CUBE) for v in face}
    active=set(vertices) if kind=='mosaic' else {key(scale(v,math.sqrt(3))) for v in TETRA}

    def signature(point):
        return tuple(dot(axis,point)>cut+1e-7 for axis in spec.axes for cut in spec.cuts)

    slots={(s.face,signature(mean(s.polygon))):i for i,s in enumerate(source.stickers)}
    polygons={}
    corner_panels={}
    for face, vs in enumerate(body(CUBE)):
        origin=mean(vs)
        inner=[add(origin,scale(add(v,scale(origin,-1)),.22 if key(v) in active else .5)) for v in vs]
        cap_diagonal={}
        cap_sides={}
        for i,v in enumerate(vs):
            if key(v) not in active:
                continue
            before=add(v,scale(add(vs[i-1],scale(v,-1)),.18))
            after=add(v,scale(add(vs[(i+1)%4],scale(v,-1)),.18))
            diagonal=add(add(before,after),scale(v,-1))
            cap_diagonal[i]=diagonal
            cap_sides[i]=(before,after)
            corner_panels[(key(v),face)]=(v,after,diagonal,before)
        for i,v in enumerate(vs):
            j=(i+1)%4
            nxt=vs[j]
            midpoint=mean((v,nxt))
            junction=add(add(inner[i],inner[j]),scale(origin,-1))
            central=(origin,inner[i],junction,inner[j])
            old_centre=mean((origin,mean((v,origin)),midpoint,mean((nxt,origin))))
            polygons[slots[(face,signature(old_centre))]]=central
            for k,other in ((i,j),(j,i)):
                corner=vs[k]
                old_point=mean((corner,midpoint,mean((corner,origin))))
                if key(corner) in active:
                    toward=cap_sides[k][1 if other==(k+1)%4 else 0]
                    poly=(toward,midpoint,junction,inner[k],cap_diagonal[k])
                else:
                    # Junction is collinear with the original triangle edge.
                    poly=(corner,midpoint,junction,inner[k])
                polygons[slots[(face,signature(old_point))]]=poly
    if len(polygons)!=len(source.stickers):
        raise ValueError('Mosaic face partition is incomplete')

    def sticker(piece,face,polygon):
        return Sticker(piece,face,tuple(polygon),triangulate(tuple(polygon),spec.normals[face]))

    stickers=[sticker(s.piece,s.face,polygons[i]) for i,s in enumerate(source.stickers)]
    pieces=list(source.pieces)
    centres=list(source.centres)
    corner_ids={}
    for vertex in sorted(active):
        piece=len(pieces)
        corner_ids[vertex]=piece
        indices=[]
        for face in range(6):
            panel=corner_panels.get((vertex,face))
            if panel is not None:
                indices.append(len(stickers))
                stickers.append(sticker(piece,face,panel))
        pieces.append(tuple(indices))
        centres.append(scale(vertices[vertex],.88))
    lookup={(s.piece,s.face):i for i,s in enumerate(stickers)}
    normals={key(normal):i for i,normal in enumerate(spec.normals)}
    permutations=[]
    layers=[]
    for axis_id,axis in enumerate(spec.axes):
        vertex=key(scale(axis,math.sqrt(3)))
        cap=corner_ids.get(vertex)
        axis_perms=[]
        axis_layers=[]
        for layer,old in enumerate(source.permutations[axis_id]):
            perm=list(old)+list(range(len(source.stickers),len(stickers)))
            band=list(source.layers[axis_id][layer])
            if cap is not None and layer==0:
                band.append(cap)
                for s in pieces[cap]:
                    destination=normals[key(rotate(spec.normals[stickers[s].face],axis,2*math.pi/3))]
                    perm[s]=lookup[(cap,destination)]
            axis_perms.append(tuple(perm))
            axis_layers.append(tuple(band))
        permutations.append(tuple(axis_perms))
        layers.append(tuple(axis_layers))
    return Geometry(spec,tuple(stickers),tuple(pieces),tuple(centres),
                    tuple(permutations),tuple(layers))
