"""Eight face axes on a truncated tetrahedron with two face families."""
import math
from functools import lru_cache
from cube.polyhedral import (Spec, OCTA, add, scale, dot, cross, mean,
                             body_faces, unit, rotate, key, clip)
from cube.prism import triangular_face_cuts


# Upright product orientation: small triangle 6 on top, triangle 5 in front.
_UP = OCTA[5]
_FRONT = unit(add(OCTA[4], scale(_UP, -dot(OCTA[4], _UP))))
_RIGHT = cross(_UP, _FRONT)
NORMALS = tuple((dot(p, _RIGHT), dot(p, _UP), dot(p, _FRONT)) for p in OCTA)


def drum_specification(n):
    if n not in (2, 3, 4, 5):
        raise ValueError('Unsupported puzzle order')
    k = n//2
    # A triangular cap's centre projects to 1/2 on each adjacent hex axis,
    # and its boundary projects to 1. Map the prism's normalized side cuts
    # through this interval, so 2/3 and 4/5 share the prism's exact cap layout.
    # Using the prism thresholds directly cuts through the cap centre and
    # invents a uniform triangular grid instead of the broad central triangle.
    radial = triangular_face_cuts(n)
    large = tuple(.5+.5*q for q in radial)
    # At depth exactly 1, a middle edge's two visible polygons meet at only
    # one point, producing a spurious triangular-looking sticker. A shallow
    # finite edge span makes ordinary corner/wing quadrilaterals, as in the
    # supplied 3/5 diagrams, without crossing into other triangular caps.
    small = tuple(1.1+.4*i/k for i in range(k))
    return Spec('war_drum', n, NORMALS, NORMALS, (), 3,
                axis_cuts=(large,)*4+(small,)*4,
                bounds=(1.,)*4+(1.5,)*4)


def drum_even_geometry(source, spec):
    from cube.polyhedral_variants import retain_pieces
    kept = []
    faces = body_faces(spec)
    for piece, slots in enumerate(source.pieces):
        # Triangular-face subdivision is retained; the hidden row is in the
        # hexagonal family and its mid-edges, rather than in all eight faces.
        if any(source.stickers[s].face >= 4 for s in slots) or len(slots) > 2:
            kept.append(piece)
            continue
        if len(slots) == 2:
            a, b = (spec.normals[source.stickers[s].face] for s in slots)
            if abs(dot(cross(a, b), source.centres[piece])) > 1e-7:
                kept.append(piece)
            continue
        sticker = source.stickers[slots[0]]
        normal = spec.normals[sticker.face]
        radial = add(source.centres[piece], scale(normal, -dot(normal, source.centres[piece])))
        if dot(radial, radial) < 1e-12:
            # The inverted triangle is the immobile hexagon centre.
            if any(perm[slots[0]] != slots[0] for axis in source.permutations for perm in axis):
                raise ValueError('Drum centre must be immobile')
            kept.append(piece)
            continue
        centre = scale(normal, spec.bounds[sticker.face])
        vertices = faces[sticker.face]
        # Remove the centres on the disappearing hexagon/hexagon mid-edges.
        aligned = False
        for a, b in zip(vertices, vertices[1:]+vertices[:1]):
            midpoint = mean((a, b))
            if any(abs(dot(n, midpoint)-d) < 1e-7
                   for n, d in zip(spec.normals[4:], spec.bounds[4:])):
                continue
            direction = add(midpoint, scale(centre, -1))
            if (dot(cross(radial, direction), cross(radial, direction)) < 1e-12
                    and dot(radial, direction) > 0):
                aligned = True
                break
        if not aligned:
            kept.append(piece)
    patches = _even_hex_patches(source, spec, kept)
    return retain_pieces(source, spec, kept, face_patches=patches)



def _even_hex_patches(source, spec, kept):
    """Continuous even-order bands around a fixed inverted triangle.

    The centre triangle is a physical sticker. Polygon triangulation and
    cut intersections do not introduce independently paintable pieces.
    The triangle caps on the other four faces are left unchanged.
    """
    k = spec.n//2
    face = 0
    normal = spec.normals[face]
    outline = body_faces(spec)[face]
    adjacent = tuple(i for i in range(4) if i != face)
    inner = spec.axis_cuts[face][0]
    centre_bound = (1+inner)/2
    kept = set(kept)
    slots = [s for s, sticker in enumerate(source.stickers)
             if sticker.face == face and sticker.piece in kept]
    expected = 10 if k == 1 else 31
    if len(slots) != expected:
        raise ValueError('Drum even hexagon piece count does not match the sketch')
    cells = []
    def cut(polygon, axis, low=None, high=None):
        if high is not None:
            polygon = clip(polygon, axis, high)
        if low is not None and polygon:
            polygon = clip(polygon, scale(axis,-1), -low)
        return polygon
    def append(polygon, faces):
        if not polygon:
            raise ValueError('Drum continuous band has no exterior region')
        cells.append((polygon, tuple(sorted(faces))))

    # The central triangle's vertices land on the three inner long-edge
    # bands. No radial fan or tiny supplementary triangle is inserted.
    core = outline
    central = outline
    for j in adjacent:
        core = cut(core, spec.normals[j], high=inner)
        central = cut(central, spec.normals[j], low=-centre_bound)
    append(central, (face,))
    central_slot = next(s for s in slots if dot(add(source.centres[source.stickers[s].piece],
                                                   scale(normal,-1)),
                                                add(source.centres[source.stickers[s].piece],
                                                   scale(normal,-1))) < 1e-12)
    for j in adjacent:
        region = cut(core, spec.normals[j], high=-centre_bound)
        if k == 1:
            append(region, (face,j+4))
        else:
            # One short-edge band and its broad inner quadrilateral. The
            # latter reaches the fixed triangle instead of ending at -1.
            depth = spec.axis_cuts[j+4][-1]
            append(cut(region, spec.normals[j], high=-depth), (face,j+4))
            append(cut(region, spec.normals[j], low=-depth), (face,))

    levels = spec.axis_cuts[face]+(spec.bounds[face],)
    for j in adjacent:
        others = tuple(i for i in adjacent if i != j)
        for layer, (low, high) in enumerate(zip(levels,levels[1:])):
            band = cut(outline, spec.normals[j], low=low, high=high)
            for near, far in (others, tuple(reversed(others))):
                half = clip(band, add(spec.normals[near],scale(spec.normals[far],-1)),0.)
                if k == 1:
                    append(half, (face,j,near+4))
                else:
                    depth = spec.axis_cuts[near+4][-1]
                    outer_faces = (face,j,near+4) if layer == k-1 else (face,near+4)
                    inner_faces = (face,j) if layer == k-1 else (face,)
                    append(cut(half,spec.normals[near],high=-depth), outer_faces)
                    append(cut(half,spec.normals[near],low=-depth), inner_faces)
    if len(cells) != len(slots):
        raise ValueError('Drum band layout creates a nonphysical sticker')

    # Assign like-coloured physical footprints. Their threefold partners are
    # assigned together, so arbitrary tie order cannot break a legal turn.
    original = {key(mean(source.stickers[s].polygon)): s for s in slots}
    faces_of = {s: tuple(sorted(source.stickers[t].face
                               for t in source.pieces[source.stickers[s].piece])) for s in slots}
    assignments = {0:central_slot}
    used = {central_slot}
    candidates = sorted((sum((a-b)**2 for a,b in zip(mean(poly),mean(source.stickers[s].polygon))),i,s)
                        for i,(poly,faces) in enumerate(cells) for s in slots
                        if i and s != central_slot and faces_of[s] == faces)
    normals = {key(n):i for i,n in enumerate(spec.normals)}
    for _,i,s in candidates:
        if i in assignments or s in used:
            continue
        orbit = []
        for turn in range(3):
            angle = turn*2*math.pi/3
            point = rotate(mean(source.stickers[s].polygon), normal, angle)
            target = original.get(key(point))
            if target is None:
                target = min(slots,key=lambda t:sum((a-b)**2 for a,b in
                             zip(point,mean(source.stickers[t].polygon))))
            polygon_point = rotate(mean(cells[i][0]),normal,angle)
            rotated_faces = tuple(sorted(normals[key(rotate(spec.normals[f],normal,angle))]
                                          for f in cells[i][1]))
            choices = [j for j,(poly,faces) in enumerate(cells) if faces == rotated_faces]
            j = min(choices,key=lambda j:sum((a-b)**2 for a,b in zip(polygon_point,mean(cells[j][0]))))
            if sum((a-b)**2 for a,b in zip(polygon_point,mean(cells[j][0]))) > 1e-9:
                raise ValueError('Drum band layout breaks threefold symmetry')
            orbit.append((j,target))
        if any(j in assignments or t in used for j,t in orbit):
            continue
        for j,t in orbit:
            assignments[j] = t
            used.add(t)
    if len(assignments) != len(slots):
        raise ValueError('Drum band layout cannot identify its physical pieces')
    patches = {s:(cells[i][0],) for i,s in assignments.items()}

    all_slots = {(sticker.face,key(source.centres[sticker.piece])):s
                 for s,sticker in enumerate(source.stickers) if sticker.piece in kept}
    result = {}
    for destination in range(4):
        frame = next(f for f in _frames()
                     if key(_transform(f,normal)) == key(spec.normals[destination]))
        for s,parts in patches.items():
            point = _transform(frame,source.centres[source.stickers[s].piece])
            target = all_slots.get((destination,key(point)))
            if target is None:
                raise ValueError('Drum exterior transport lost a physical piece')
            result[target] = tuple(tuple(_transform(frame,p) for p in poly) for poly in parts)
    return result


@lru_cache(maxsize=1)
def _frames():
    identity = ((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    frames = [identity]
    seen = {tuple(key(v) for v in identity)}
    for frame in frames:
        for axis in NORMALS[:2]:
            nxt = tuple(rotate(v,axis,2*math.pi/3) for v in frame)
            signature = tuple(key(v) for v in nxt)
            if signature not in seen:
                seen.add(signature)
                frames.append(nxt)
    return tuple(frames)


def _transform(frame,point):
    return tuple(sum(frame[j][i]*point[j] for j in range(3)) for i in range(3))
