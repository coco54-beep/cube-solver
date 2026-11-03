"""Geometric definitions of deep-cut minxes and the two Dogic colourways."""
from functools import lru_cache
import math

from cube.polyhedral import (Spec, Geometry, Sticker, DODECA, CUBE, OCTA, body, unit, key,
                            mean, add, scale, dot, rotate)


@lru_cache(maxsize=1)
def dodeca_vertices():
    return tuple({key(unit(v)): unit(v) for face in body(DODECA) for v in face}.values())


def specification(kind, n):
    if n != 3:
        raise ValueError('Unsupported puzzle order')
    if kind == 'pyraminx_crystal':
        return Spec(kind, n, DODECA, DODECA, (1/math.sqrt(5),), 5)
    if kind == 'master_brilic':
        # The Crystal's deep floating-edge layer plus a shallow Minx layer.
        # Thirty coloured facets per face, matching TomZ's 360-tile model.
        shallow=(3+4*math.sqrt((5-2*math.sqrt(5))/(5+2*math.sqrt(5))))/5
        return Spec(kind,n,DODECA,DODECA,(1/math.sqrt(5),shallow),5)
    if kind == 'pentultimate':
        return Spec(kind, n, DODECA, DODECA, (0.,), 5)
    if kind == 'master_pentultimate':
        inradius=.7*math.sqrt((5+2*math.sqrt(5))/15)
        return Spec(kind, n, DODECA, DODECA, (.06/inradius,), 5)
    if kind == 'starminx_i':
        ratio=math.sqrt((5-2*math.sqrt(5))/(5+2*math.sqrt(5)))
        return Spec(kind,n,DODECA,DODECA,(ratio,),5)
    if kind == 'dinominx':
        return Spec(kind, n, DODECA, dodeca_vertices(),
                    (math.sqrt(5*(5-2*math.sqrt(5))/3),), 3)
    raise ValueError('Unsupported expanded polyhedron')


def assemble(spec, panels, pieces, centres, selected, origins=None):
    """Build exact panel actions from a rigid geometric rotation.

    Every transformed panel must match a complete destination polygon. The
    builder rejects overlaps, missing panels and split physical pieces.
    """
    def polygon_key(poly):
        return tuple(sorted(key(p) for p in poly))
    lookup = {polygon_key(s.polygon): i for i, s in enumerate(panels)}
    if len(lookup) != len(panels):
        raise ValueError('Duplicate expanded panel')
    permutations = []
    for axis_id, layers in enumerate(selected):
        axis = spec.axes[axis_id]
        angle = 2*math.pi/spec.order(axis_id)
        origin = origins[axis_id] if origins else (0., 0., 0.)
        rows = []
        for layer in layers:
            row = []
            moving = set(layer)
            for i, s in enumerate(panels):
                if s.piece not in moving:
                    row.append(i)
                    continue
                rotated = tuple(add(origin, rotate(add(p, scale(origin, -1)), axis, angle))
                                for p in s.polygon)
                target = lookup.get(polygon_key(rotated))
                if target is None:
                    raise ValueError(('Expanded layer is not closed', spec.kind, axis_id, i))
                row.append(target)
            if sorted(row) != list(range(len(panels))):
                raise ValueError('Expanded turn is not bijective')
            for piece in pieces:
                if len({panels[row[i]].piece for i in piece}) != 1:
                    raise ValueError('Expanded turn splits a physical piece')
            rows.append(tuple(row))
        permutations.append(tuple(rows))
    return Geometry(spec, tuple(panels), tuple(pieces), tuple(centres),
                    tuple(permutations), tuple(tuple(tuple(sorted(b)) for b in a) for a in selected))


@lru_cache(maxsize=1)
def dogic_physical_layout():
    """One 80-piece mechanism for BOTH colourways; inlays are not cuts."""
    normals = dodeca_vertices()
    parts=[]
    for face,triangle in enumerate(body(normals)):
        mids = tuple(mean((a, b)) for a, b in zip(triangle, triangle[1:]+triangle[:1]))
        owner_axes = tuple(max(range(12), key=lambda i: dot(DODECA[i], v)) for v in triangle)
        for corner, vertex in enumerate(triangle):
            parts.append((face,(vertex,mids[corner],mids[corner-1]),owner_axes[corner]))
        parts.append((face,mids,None))
    selected=[]
    for axis_id,axis in enumerate(DODECA):
        touching={f for f,triangle in enumerate(body(normals))
                  if any(dot(unit(v),axis)>1-1e-7 for v in triangle)}
        tips=tuple(i for i,(face,poly,owner) in enumerate(parts) if owner==axis_id)
        cap=tuple(i for i,(face,poly,owner) in enumerate(parts) if face in touching)
        selected.append((tips,cap))
    return normals,tuple(parts),tuple(selected)


@lru_cache(maxsize=2)
def dogic_geometry(kind):
    if kind not in ('dogic_i', 'dogic_20'):
        raise ValueError('Unsupported Dogic')
    normals,parts,selected=dogic_physical_layout()
    spec = Spec(kind,3,normals,DODECA,(),5)
    panels,pieces,centres=[],[],[]
    for p,(face,poly,owner) in enumerate(parts):
        if owner is not None:
            pieces.append((len(panels),))
            panels.append(Sticker(p, face, poly))
        elif kind=='dogic_i':
            pivot=mean(poly);slots=[]
            # Three paint regions on the same uncut central triangle. The
            # 20-colour variant paints this complete physical face one colour.
            for corner in range(3):
                inlay=(pivot,poly[corner-1],poly[corner])
                slots.append(len(panels));panels.append(Sticker(p,face,inlay))
            pieces.append(tuple(slots))
        else:
            pieces.append((len(panels),));panels.append(Sticker(p,face,poly))
        centres.append(mean(poly))
    return assemble(spec, panels, pieces, centres, selected)


@lru_cache(maxsize=2)
def dogic_physical_outlines(kind):
    """Show the same cuts in grey, painted, teaching and playback views.

    Repeating an outer outline for each central inlay also highlights the
    complete rigid triangle when a coloured region is selected. No radial
    colour boundary is ever drawn as a mechanical seam.
    """
    _,parts,_=dogic_physical_layout();g=dogic_geometry(kind)
    return tuple(tuple(zip(parts[s.piece][1],parts[s.piece][1][1:]+parts[s.piece][1][:1]))
                 for s in g.stickers)


def dogic_colors(cube):
    if cube.puzzle_kind == 'dogic_20':
        return tuple(s.face for s in cube.geometry.stickers)
    return tuple(max(range(12), key=lambda a: dot(DODECA[a], mean(s.polygon)))
                 for s in cube.geometry.stickers)


@lru_cache(maxsize=1)
def diamond_geometry():
    """Oskar's Pyraminx Diamond: cube corners/centres in an octahedral shell.

    Six four-sticker tips and eight independent central triangles. Each
    quarter turn carries one tip and its four adjacent central triangles.
    It is distinct from the face-turning Skewb Diamond/FTO family.
    """
    from cube.polyhedral import _cut_skin
    from collections import defaultdict
    spec=Spec('pyraminx_diamond',3,OCTA,CUBE,(math.sqrt(3)/2,),4)
    groups=defaultdict(list)
    for signature,face,poly in _cut_skin(spec):
        groups[signature if any(signature) else ('centre',face)].append((face,poly))
    panels=[];pieces=[];centres=[]
    for group in groups.values():
        p=len(pieces);slots=[]
        for face,poly in group:
            slots.append(len(panels));panels.append(Sticker(p,face,poly))
        pieces.append(tuple(slots))
        centres.append(mean(tuple({key(v):v for f,poly in group for v in poly}.values())))
    selected=[]
    for axis in CUBE:
        tip=max((i for i,p in enumerate(pieces) if len(p)==4),key=lambda i:dot(axis,centres[i]))
        selected.append(({tip}|{i for i,p in enumerate(pieces) if len(p)==1 and dot(axis,centres[i])>1e-7},))
    return assemble(spec,panels,pieces,centres,selected)
