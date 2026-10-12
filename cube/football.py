"""Thirty-two-face Tuttminx geometry with pentagon and hexagon axes."""
from functools import lru_cache
from cube.polyhedral import (DODECA,body,unit,key,dot,add,scale,Spec,Geometry,
                             Sticker,geometry,mean,clip,body_faces,cross,EPS)

@lru_cache(maxsize=1)
def shell_planes():
    faces=body(DODECA)
    normals=tuple({key(unit(v)):unit(v) for face in faces for v in face}.values())
    neighbor=next(v for v in DODECA if .4<dot(v,DODECA[0])<.5)
    corner=scale(add(scale(DODECA[0],2),neighbor),1/3)
    pentagon=dot(DODECA[0],corner)
    hexagon=max(dot(v,DODECA[0]) for v in normals)
    return tuple((n,1.,1) for n in DODECA)+tuple((n,hexagon/pentagon,0) for n in normals)

@lru_cache(maxsize=1)
def shell_faces():
    planes=shell_planes()
    polygons=body(tuple(scale(n,1/bound) for n,bound,color in planes))
    return tuple((p,color) for p,(_,_,color) in zip(polygons,planes))

def football_point(p):
    factor=min(bound/dot(n,p) for n,bound,color in shell_planes() if dot(n,p)>1e-9)
    return scale(p,factor)


def football_specification(n):
    if n not in (3,5):
        raise ValueError('Football puzzles support orders 3 and 5 only')
    planes=shell_planes()
    normals=tuple(n for n,_,_ in planes)
    bounds=tuple(d for _,d,_ in planes)
    # A shared 24-degree unit represents 72-degree pentagon moves and
    # 120-degree hexagon moves without permitting 60-degree illegal turns.
    # Keep the inner cut at the classical Tuttminx depth and split its cap
    # once more. The former .87/.94 pair intersected additional hexagon
    # edge regions, inventing 90 pieces that are absent on a Rayminx.
    fractions=(.9,) if n==3 else (.9,.95)
    cuts=tuple(tuple(d*f for f in fractions) for d in bounds)
    return Spec('football',n,normals,normals,(),15,False,
                (3,)*12+(5,)*20,cuts,bounds)


def even_football_geometry(n):
    """Kilo and Master variants retain whole movable corner/wing orbits."""
    odd=geometry('football',n+1)
    spec=football_specification(n)
    kept=[]
    faces=body_faces(spec)
    for piece,slots in enumerate(odd.pieces):
        if len(slots)==3:
            kept.append(piece)
        elif n==4 and len(slots)==2:
            a,b=(spec.normals[odd.stickers[s].face] for s in slots)
            if abs(dot(cross(a,b),odd.centres[piece]))>EPS:
                kept.append(piece)
        elif n==4 and len(slots)==1:
            s=odd.stickers[slots[0]]
            normal=spec.normals[s.face]
            radial=add(odd.centres[piece],scale(normal,-dot(normal,odd.centres[piece])))
            if dot(radial,radial)<EPS:
                continue
            centre=scale(normal,spec.bounds[s.face])
            directions=[add(mean((a,b)),scale(centre,-1))
                        for a,b in zip(faces[s.face],faces[s.face][1:]+faces[s.face][:1])]
            if not any(dot(cross(radial,d),cross(radial,d))<EPS*EPS and dot(radial,d)>0
                       for d in directions):
                kept.append(piece)
    piece_ids={p:i for i,p in enumerate(kept)}
    retained=tuple(s for piece in kept for s in odd.pieces[piece])
    sticker_ids={s:i for i,s in enumerate(retained)}
    polygons={}
    # A symmetric, closed partition expands retained stickers over regions
    # occupied by the removed middle pieces. Boundaries are shared exactly.
    for face,outline in enumerate(faces):
        slots=[s for s in retained if odd.stickers[s].face==face]
        positions={s:mean(odd.stickers[s].polygon) for s in slots}
        for s in slots:
            p=positions[s]
            poly=outline
            for other in slots:
                if other==s:
                    continue
                q=positions[other]
                axis=add(q,scale(p,-1))
                poly=clip(poly,axis,(dot(q,q)-dot(p,p))/2)
                if not poly:
                    raise ValueError('A retained football sticker has no face region')
            polygons[s]=poly
    stickers=tuple(Sticker(piece_ids[odd.stickers[s].piece],odd.stickers[s].face,polygons[s])
                   for s in retained)
    pieces=tuple(tuple(sticker_ids[s] for s in odd.pieces[p]) for p in kept)
    permutations=[]
    layers=[]
    for axis in odd.permutations:
        perms=[]
        bands=[]
        for perm in axis:
            if any(perm[s] not in sticker_ids for s in retained):
                raise ValueError('Football retained pieces do not form closed turn orbits')
            projected=tuple(sticker_ids[perm[s]] for s in retained)
            if projected==tuple(range(len(retained))):
                continue
            perms.append(projected)
            bands.append(tuple(sorted({piece_ids[odd.stickers[s].piece] for s in retained if perm[s]!=s})))
        permutations.append(tuple(perms))
        layers.append(tuple(bands))
    return Geometry(spec,stickers,pieces,tuple(odd.centres[p] for p in kept),
                    tuple(permutations),tuple(layers))
