"""Solve a colour-entered Void Megaminx (centres removed).

The missing centres leave the global colour frame ambiguous, so each body
orientation supplies a virtual set of centre colours. A frame that passes the
ordinary Megaminx identification is solved with the regular solver, and only a
solution that replays on the centreless model is accepted.
"""
from functools import lru_cache
from cube.polyhedral import PolyhedralPuzzle, key
from solver.polyhedral import identify, _body_frames, _transform, solve_minx


@lru_cache(maxsize=1)
def _embedding():
    void = PolyhedralPuzzle('void_minx', 3).geometry
    full = PolyhedralPuzzle("megaminx", 3)
    solid = full.geometry
    kept = [i for i, slots in enumerate(solid.pieces) if len(slots) > 1]
    piece_index = {p: i for i, p in enumerate(kept)}
    void_sticker = {(sticker.piece, sticker.face): i
                    for i, sticker in enumerate(void.stickers)}
    face_index = {key(normal): i for i, normal in enumerate(solid.spec.normals)}
    mapping = tuple((index, void_sticker[(piece_index[sticker.piece], sticker.face)])
                    for index, sticker in enumerate(solid.stickers)
                    if len(solid.pieces[sticker.piece]) > 1)
    centers = tuple((slots[0], solid.stickers[slots[0]].face)
                    for slots in solid.pieces if len(slots) == 1)
    frames = tuple(tuple((slot, face_index[key(_transform(frame, solid.spec.normals[face]))])
                         for slot, face in centers)
                   for frame in _body_frames('void_minx', 3))
    return mapping, frames


def solve_void_minx(cube, cancel=None, progress=None):
    identify(cube)
    if cube.is_solved():
        return ()
    full = PolyhedralPuzzle('megaminx', 3)
    mapping, frames = _embedding()
    base_colors = [-1] * len(full.colors)
    for target, source in mapping:
        base_colors[target] = cube.colors[source]
    for stage, frame in enumerate(frames):
        if cancel and cancel():
            raise InterruptedError()
        if progress:
            progress(stage, len(frames))
        colors = list(base_colors)
        for slot, color in frame:
            colors[slot] = color
        full.colors = colors
        try:
            identify(full)
        except ValueError:
            continue
        try:
            word = solve_minx(full, cancel, None, optimize=False)
        except ValueError:
            # Identifiable colours alone do not establish the permutation
            # constraints of the chosen virtual centre frame.
            continue
        if len(word) > 150:
            from solver.polyhedral_optimize import optimize_solution
            word = optimize_solution(full, word,
                                     lambda work: solve_minx(work, cancel, None, optimize=False),
                                     budget=.8, target=150, cancel=cancel)
        replay = cube.entered()
        for move in word:
            replay.apply_move(move)
        if replay.is_solved():
            return word
    raise ValueError("The entered puzzle is not a legal state")
