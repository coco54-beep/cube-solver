"""Rigid, offset-shell Pyraminx models with independently turning tips."""
from functools import lru_cache
import math

from cube.mastermorphix import IDENTITY, transform
from cube.mirror_tower import (Piece, frames, frame_key, multiply, transpose,
                               _clip_solid)
from cube.polyhedral import geometry, body, add, scale, dot, rotate, Move, Sticker, Geometry

SHELL_OFFSET = (-.12, -.08, .05)
SHELL_OFFSETS = {'pyraminx': SHELL_OFFSET, 'skewb': (.22, -.13, .08)}


@lru_cache(maxsize=512)
def piece_faces(n, home, kind='pyraminx'):
    g = geometry(kind, n)
    offset = SHELL_OFFSETS[kind]
    polygons = [(tuple(add(p, offset) for p in face), 0) for face in body(g.spec.normals)]
    centre = g.centres[home]
    for axis in g.spec.axes:
        value = dot(axis, centre)
        below = [cut for cut in g.spec.cuts if cut < value - 1e-8]
        above = [cut for cut in g.spec.cuts if cut > value + 1e-8]
        if below:
            polygons = _clip_solid(polygons, scale(axis, -1), -max(below))
        if above:
            polygons = _clip_solid(polygons, axis, min(above))
    return tuple(polygons)


@lru_cache(maxsize=2)
def marker_system(n, kind='pyraminx'):
    g = geometry(kind, n)
    points = []
    pending = set(range(len(g.pieces)))
    orbit = 0
    while pending:
        home = min(pending)
        members = set()
        for frame in frames():
            point = transform(frame, g.centres[home])
            position = min(range(len(g.pieces)), key=lambda i: sum((a-b)**2 for a, b in zip(g.centres[i], point)))
            if sum((a-b)**2 for a, b in zip(g.centres[position], point)) > 1e-9:
                raise ValueError('Mirror piece orbit is not tetrahedrally symmetric')
            points.append((orbit, position, frame))
            members.add(position)
        # Independent tips form singleton *move* orbits, but belong to one
        # tetrahedral geometry orbit. Their other two frames are real tip
        # directions, not missing positions or an impossible input state.
        if not members <= pending:
            raise ValueError('Overlapping mirror geometry orbits')
        pending.difference_update(members)
        orbit += 1
    index = {(orbit, frame_key(frame)): i for i, (orbit, _, frame) in enumerate(points)}
    permutations = []
    for axis, layers in enumerate(g.layers):
        turn = tuple(rotate(v, g.spec.axes[axis], 2*math.pi/3) for v in IDENTITY)
        permutations.append(tuple(tuple(index[(orbit, frame_key(multiply(turn, frame)))]
                                        if position in layer else i
                                        for i, (orbit, position, frame) in enumerate(points))
                                  for layer in layers))
    markers = tuple(Sticker(position, i, ()) for i, (_, position, _) in enumerate(points))
    pieces = tuple(tuple(i for i, (_, position, _) in enumerate(points) if position == p)
                   for p in range(len(g.pieces)))
    virtual = Geometry(g.spec, markers, pieces, g.centres, tuple(permutations), g.layers)
    return tuple(points), index, virtual


@lru_cache(maxsize=4096)
def placements(n, home, position, kind='pyraminx'):
    g = geometry(kind, n)
    return tuple(frame for frame in frames()
                 if sum((a-b)**2 for a, b in zip(transform(frame, g.centres[home]),
                                                 g.centres[position])) < 1e-9)


class MirrorPyraminxCube:
    puzzle_kind = 'mirror_pyraminx'
    mechanism_kind = 'pyraminx'
    supported_orders = (3, 4)
    color_count = 4

    def __init__(self, pieces=None, n=3):
        if n not in self.supported_orders:
            raise ValueError('Unsupported mirror puzzle order')
        self.n = n
        self.geometry = geometry(self.mechanism_kind, n)
        self.pieces = (dict(pieces) if pieces is not None else
                       {p: Piece(p) for p in range(len(self.geometry.pieces))})

    @classmethod
    def solved(cls, n=3):
        return cls(n=n)

    def clone(self):
        return type(self)(self.pieces, self.n)

    entered = clone

    def piece_faces(self, home):
        return piece_faces(self.n, home, self.mechanism_kind)

    def moves(self):
        return tuple(Move(axis, layer) for axis, layers in enumerate(self.geometry.layers)
                     for layer in range(len(layers)))

    def ordinary_state(self):
        """Virtual face colours for the first stage; silver input stays shaped."""
        from cube.polyhedral import PolyhedralPuzzle, key
        g = self.geometry
        normals = {key(normal): face for face, normal in enumerate(g.spec.normals)}
        colors = [-1] * len(g.stickers)
        for position, piece in self.pieces.items():
            slots = {g.stickers[s].face: s for s in g.pieces[position]}
            for source in g.pieces[piece.home]:
                home_face = g.stickers[source].face
                face = normals[key(transform(piece.frame, g.spec.normals[home_face]))]
                colors[slots[face]] = home_face
        return PolyhedralPuzzle(self.mechanism_kind, self.n, colors)

    def apply_move(self, move):
        g = self.geometry
        permutation = g.permutation(move)
        turn = tuple(rotate(v, g.spec.axes[move.axis], 2*math.pi*(move.amount % 3)/3) for v in IDENTITY)
        canonical = {frame_key(frame): frame for frame in frames()}
        result = dict(self.pieces)
        for position in g.layers[move.axis][move.layer]:
            piece = self.pieces[position]
            target = g.stickers[permutation[g.pieces[position][0]]].piece
            result[target] = Piece(piece.home, canonical[frame_key(multiply(turn, piece.frame))])
        self.pieces = result
        return self

    def labeled_state(self):
        points, index, _ = marker_system(self.n, self.mechanism_kind)
        expected = set(range(len(self.geometry.pieces)))
        if set(self.pieces) != expected:
            raise ValueError('Incomplete mirror piece state')
        by_home = {piece.home: piece for piece in self.pieces.values()}
        if set(by_home) != expected:
            raise ValueError('Duplicate mirror piece')
        for position, piece in self.pieces.items():
            if frame_key(piece.frame) not in {frame_key(f) for f in placements(self.n, piece.home, position, self.mechanism_kind)}:
                raise ValueError('Impossible mirror piece orientation')
        return tuple(index[(orbit, frame_key(multiply(by_home[home].frame, frame)))]
                     for orbit, home, frame in points)

    @property
    def colors(self):
        state = self.labeled_state()
        values = [0] * len(state)
        for source, destination in enumerate(state):
            values[destination] = source
        return values

    @colors.setter
    def colors(self, values):
        points, _, _ = marker_system(self.n, self.mechanism_kind)
        if sorted(values) != list(range(len(points))):
            raise ValueError('Incomplete mirror piece state')
        state = [0] * len(values)
        for destination, source in enumerate(values):
            state[source] = destination
        pieces = {}
        homes = set()
        for source, (orbit, home, frame) in enumerate(points):
            if home in homes:
                continue
            target_orbit, position, target_frame = points[state[source]]
            if target_orbit != orbit or position in pieces:
                raise ValueError('Invalid mirror piece state')
            pieces[position] = Piece(home, multiply(target_frame, transpose(frame)))
            homes.add(home)
        check = type(self)(pieces, self.n)
        if check.labeled_state() != tuple(state):
            raise ValueError('Inconsistent mirror piece orientation')
        self.pieces = pieces

    def is_solved(self):
        return (len(self.pieces) == len(self.geometry.pieces) and
                all(piece.home == position and frame_key(piece.frame) == frame_key(IDENTITY)
                    for position, piece in self.pieces.items()))
