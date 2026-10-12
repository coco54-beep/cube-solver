"""Closed retained orbits and face patches for even-order shape variants."""
from collections import defaultdict

from cube.polyhedral import Geometry, Sticker, mean


def retain_pieces(source, spec, kept, face_patches=None):
    kept = tuple(kept)
    piece_index = {p: i for i, p in enumerate(kept)}
    retained = tuple(s for p in kept for s in source.pieces[p])
    index = {s: i for i, s in enumerate(retained)}
    patches = {s: list(source.stickers[s].patches or (source.stickers[s].polygon,))
               for s in retained}
    by_face = defaultdict(list)
    for s in retained:
        by_face[source.stickers[s].face].append(s)
    face_patches = face_patches or {}
    replaced_faces = {source.stickers[s].face for s in face_patches}
    # Divide each omitted patch about its centre. The triangle's centroid
    # selects a nearby retained sticker without leaving a black hole.
    for old, sticker in enumerate(source.stickers):
        if old in index:
            continue
        if sticker.face in replaced_faces:
            continue
        candidates = by_face[sticker.face]
        for patch in sticker.patches or (sticker.polygon,):
            centre = mean(patch)
            for a, b in zip(patch, patch[1:]+patch[:1]):
                triangle = (centre, a, b)
                midpoint = mean(triangle)
                owner = min(candidates, key=lambda s: sum((x-y)**2 for x, y in
                            zip(midpoint, mean(source.stickers[s].polygon))))
                patches[owner].append(triangle)
    polygons = {s: source.stickers[s].polygon for s in retained}
    for s, parts in face_patches.items():
        if s not in index or not parts:
            raise ValueError('Exterior patch has no retained physical sticker')
        patches[s] = list(parts)
        polygons[s] = max(parts, key=len)
    permutations, layers = [], []
    for axis in source.permutations:
        perms, bands = [], []
        for perm in axis:
            if any(perm[s] not in index for s in retained):
                raise ValueError('Even variant removes part of a movable orbit')
            p = tuple(index[perm[s]] for s in retained)
            if p == tuple(range(len(p))):
                continue
            perms.append(p)
            bands.append(tuple(sorted({piece_index[source.stickers[s].piece]
                                      for s in retained if perm[s] != s})))
        permutations.append(tuple(perms))
        layers.append(tuple(bands))
    stickers = tuple(Sticker(piece_index[source.stickers[s].piece],
                             source.stickers[s].face, polygons[s],
                             tuple(patches[s])) for s in retained)
    return Geometry(spec, stickers,
                    tuple(tuple(index[s] for s in source.pieces[p]) for p in kept),
                    tuple(source.centres[p] for p in kept),
                    tuple(permutations), tuple(layers))
