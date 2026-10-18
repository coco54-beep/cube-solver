"""Tangent-circle petal icosahedron, with regular edge half turns.

Each triangular face has three petals, three edge-cap stickers and one
movable triangular centre. Circular boundary segments meet the straight
outer edges tangentially; their inner ends terminate at the centre triangle.
The central triangle's visual size is approximate, based on the reference.
Partial turns and jumbling are outside this model.
"""
from functools import lru_cache
import math

from cube.polyhedral import (DODECA, TETRA, Geometry, Spec, Sticker, add, body, cross,
                             dot, key, mean, rotate, scale, unit, _patch_faces)


def _arc(centre, a, b, normal):
    u, v = add(a, scale(centre, -1)), add(b, scale(centre, -1))
    angle = math.atan2(dot(cross(u, v), normal), dot(u, v))
    tangent = cross(normal, u)
    return (a,) + tuple(add(centre, add(scale(u, math.cos(angle * j / 24)),
                                       scale(tangent, math.sin(angle * j / 24))))
                        for j in range(1, 24)) + (b,)


def _tangent_arc(a, b, edge, normal):
    """Circle through a and b, tangent to the outer edge at a."""
    radial = cross(normal, unit(edge))
    delta = add(b, scale(a, -1))
    denominator = 2 * dot(delta, radial)
    if abs(denominator) < 1e-10:
        raise ValueError('Cannot fit a tangent petal arc')
    centre = add(a, scale(radial, dot(delta, delta) / denominator))
    if abs(dot(add(a, scale(centre, -1)), edge)) > 1e-8:
        raise ValueError('Petal circle must meet the outer edge tangentially')
    return _arc(centre, a, b, normal)


@lru_cache(maxsize=4)
def petal_geometry(include_centre=True, solid='icosahedron'):
    """Build the user's regular edge-turn model for a triangular solid.

    The tetrahedron follows the user-confirmed half-turn rule. This is not
    a simulation of the LanLan jumbling-only twelve-axis mechanism.
    """
    if solid == 'tetrahedron':
        normals = TETRA
    elif solid == 'icosahedron':
        normals = tuple({key(unit(v)): unit(v) for f in body(DODECA) for v in f}.values())
    else:
        raise ValueError('Unsupported petal solid')
    faces = body(normals)
    edge_centres = {key(mean((a, b))): mean((a, b)) for face in faces
                    for a, b in zip(face, face[1:] + face[:1])}
    axes = tuple(unit(p) for p in edge_centres.values())
    edge_ids = {edge: i for i, edge in enumerate(edge_centres)}
    kind = 'petal_' + solid + ('' if include_centre else '_nocentre')
    spec = Spec(kind, 3, normals, axes, (), 2)
    groups = {}
    for face_id, vertices in enumerate(faces):
        normal = normals[face_id]
        origin = mean(vertices)
        edges = tuple(mean((a, b)) for a, b in
                      zip(vertices, vertices[1:] + vertices[:1]))
        ids = tuple(edge_ids[key(p)] for p in edges)
        # An inverted centre triangle separates the six curved surface pieces.
        # One tenth of the face circumradius approximates the supplied photo;
        # the centre is a real sticker/piece, never an empty intersection.
        inner = tuple(add(origin, scale(add(v, scale(origin, -1)), -.10 if include_centre else 0))
                      for v in vertices)
        left = tuple(_tangent_arc(a, inner[(i+2) % 3],
                                 add(vertices[(i+1) % 3], scale(a, -1)), normal)
                     for i, a in enumerate(vertices))
        right = tuple(_tangent_arc(a, inner[(i+1) % 3],
                                  add(vertices[i-1], scale(a, -1)), normal)
                      for i, a in enumerate(vertices))
        for i, a in enumerate(vertices):
            leaf = left[i] + ((inner[(i+1) % 3],) if include_centre else ()) + tuple(reversed(right[i][:-1]))
            group = ('leaf', face_id, i)
            groups[group] = [(face_id, leaf, frozenset((ids[i-1], ids[i])))]
            b = vertices[(i+1) % 3]
            cap = (a, b) + right[(i+1) % 3][1:] + tuple(reversed(left[i][:-1]))
            groups.setdefault(('cap', ids[i]), []).append((face_id, cap, frozenset((ids[i],))))
        if include_centre:
            groups[('centre', face_id)] = [(face_id, inner, frozenset(ids))]
    stickers, pieces, centres, memberships = [], [], [], []
    for group in groups.values():
        piece = len(pieces)
        points = {key(p): p for _, polygon, _ in group for p in polygon}
        centres.append(mean(tuple(points.values())))
        memberships.append(group[0][2])
        slots = []
        for face, polygon, _ in sorted(group):
            slots.append(len(stickers))
            stickers.append(Sticker(piece, face, polygon))
        pieces.append(tuple(slots))
    slots = {(s.piece, s.face): i for i, s in enumerate(stickers)}
    face_ids = {key(n): i for i, n in enumerate(normals)}
    permutations, layers = [], []
    for axis_id, axis in enumerate(axes):
        band = {p for p, membership in enumerate(memberships) if axis_id in membership}
        destinations = {}
        for p in band:
            target = rotate(centres[p], axis, math.pi)
            distance, destination = min((dot(add(q, scale(target, -1)),
                                             add(q, scale(target, -1))), i)
                                        for i, q in enumerate(centres))
            if distance > 1e-12 or destination not in band:
                raise ValueError('Petal geometry does not close under its edge turn')
            destinations[p] = destination
        face_map = [face_ids[key(rotate(n, axis, math.pi))] for n in normals]
        permutation = tuple(slots[destinations[s.piece], face_map[s.face]]
                            if s.piece in band else i for i, s in enumerate(stickers))
        if len(set(permutation)) != len(stickers) or any(
                permutation[permutation[i]] != i for i in range(len(stickers))):
            raise ValueError('Petal edge half turn must be a bijective involution')
        permutations.append((permutation,))
        layers.append((tuple(sorted(band)),))
    return _patch_faces(Geometry(spec, tuple(stickers), tuple(pieces), tuple(centres),
                                 tuple(permutations), tuple(layers)))
