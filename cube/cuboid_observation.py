"""Six orthographic observations, independent of hidden brick identities.

Coordinates describe the physical shell. A grid sample is not a puzzle piece.
Matching uses the existing model's rigid pieces, visibility and cut boundaries;
it never recovers a state from a remembered scramble.
"""
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from time import monotonic

from cube.appearance import ROTATIONS
from cube.coordinates import FACE_SPEC
from cube.cuboid import CuboidCube, FACES, IDENTITY, layout, multiply, transform, turn_frame
from cube.polyhedral import CUBE

UNKNOWN, EMPTY, PLASTIC = -1, -2, -3
FACE_ORDER = (2, 1, 5, 4, 0, 3)


def bits(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


@dataclass(frozen=True)
class Placement:
    piece: int
    frame: tuple
    core: int
    body: int
    # Each outward-facing rectangle: projected sample mask, depth, colour.
    views: tuple


@dataclass
class MatchResult:
    status: str
    cube: object = None
    face: int = None
    cell: int = None
    nodes: int = 0


@lru_cache(maxsize=3)
def observation_model(kind):
    cube = CuboidCube.solved(kind)
    cells, boxes, entries, lookup, base = layout(kind)
    # Preserve the model's axis restrictions when finding possible orientations.
    frames = {IDENTITY}
    todo = [IDENTITY]
    while todo:
        frame = todo.pop()
        for axis in range(3):
            candidate = multiply(turn_frame(axis, base.spec.step(axis)), frame)
            if candidate not in frames:
                frames.add(candidate); todo.append(candidate)
    frames = tuple(f for f in ROTATIONS if f in frames)
    extents = []
    for piece, box in enumerate(boxes):
        for frame in frames:
            if kind == 'cuboid_133':
                centre = tuple((lo+hi)/2 for lo, hi in box)
                if centre == (0., 0., 0.) and frame != IDENTITY:
                    continue
                if sum(v != 0 for v in centre) <= 1 and transform(frame, centre) != centre:
                    continue
            corners = [transform(frame, p) for p in product(*box)]
            bounds = tuple((min(p[a] for p in corners), max(p[a] for p in corners)) for a in range(3))
            extents.append((piece, frame, bounds))
    edges = tuple(tuple(sorted({v for _, _, box in extents for v in box[a]})) for a in range(3))
    edge_index = tuple({v: i for i, v in enumerate(axis)} for axis in edges)
    sizes = tuple(len(axis)-1 for axis in edges)
    values = tuple(2*i-(cube.core_n-1) for i in range(cube.core_n))
    core_points = ({transform(frame, p) for group in cells for p in group for frame in frames}
                   if getattr(cube, 'panel_anchored', False) else set(product(values, repeat=3)))
    core_index = {p: i for i, p in enumerate(sorted(core_points))}
    home_panels = {(s.piece, s.face) for s in base.stickers}
    shapes = tuple((sizes[FACE_SPEC[face][4]], sizes[FACE_SPEC[face][2]]) for face in FACES)
    placements = [[] for _ in cells]
    seen = [{} for _ in cells]
    by_frame = [{} for _ in cells]
    levels = [set() for _ in FACES]
    for piece, frame, bounds in extents:
        spans = [range(edge_index[a][lo], edge_index[a][hi]) for a, (lo, hi) in enumerate(bounds)]
        body = sum(1 << ((x*sizes[1]+y)*sizes[2]+z) for x, y, z in product(*spans))
        if kind == 'cuboid_133':
            centre = tuple((lo+hi)/2 for lo, hi in boxes[piece])
            core = 1 << core_index[transform(frame, tuple(2*v for v in centre))]
        else:
            core = sum(1 << core_index[transform(frame, p)] for p in cells[piece])
        views = []
        for face, normal in enumerate(CUBE):
            axis, sign, ra, rs, ca, cs = FACE_SPEC[FACES[face]]
            width, height = shapes[face]
            mask = 0
            for row, col in product(spans[ra], spans[ca]):
                r = row if rs > 0 else height-1-row
                c = col if cs > 0 else width-1-col
                mask |= 1 << (r*width+c)
            depth = bounds[axis][1] if sign > 0 else -bounds[axis][0]
            original = tuple(sum(normal[a]*frame[j][a] for a in range(3)) for j in range(3))
            home_face = CUBE.index(original)
            ha, hs = next((a, v) for a, v in enumerate(original) if v)
            color = home_face if (piece, home_face) in home_panels else PLASTIC
            views.append((mask, depth, color)); levels[face].add(depth)
        signature = (core, body, tuple(views))
        if signature in seen[piece]:
            by_frame[piece][frame] = seen[piece][signature]
            continue
        candidate = Placement(piece, frame, core, body, tuple(views))
        seen[piece][signature] = candidate
        by_frame[piece][frame] = candidate
        placements[piece].append(candidate)
    return {'kind': kind, 'edges': edges, 'shapes': shapes,
            'levels': tuple(tuple(sorted(v, reverse=True)) for v in levels),
            'placements': tuple(tuple(p) for p in placements), 'by_frame': tuple(by_frame)}


def project(cube, model=None):
    """Exact visible samples of a model state, including exposed black walls."""
    model = model or observation_model(cube.puzzle_kind)
    output = [[(EMPTY, 0, None) for _ in range(w*h)] for w, h in model['shapes']]
    cells, boxes, entries, lookup, _ = layout(cube.puzzle_kind)
    for piece, frame in enumerate(cube.frames):
        placement = model['by_frame'][piece].get(frame)
        if placement is None:
            raise ValueError('six.model_mismatch')
        for face, (mask, depth, color) in enumerate(placement.views):
            if color >= 0:
                if getattr(cube, 'panel_anchored', False):
                    color = cube.colors[lookup[piece, color]]
                    for index in bits(mask):
                        if output[face][index][2] is None or depth > output[face][index][2]:
                            output[face][index] = (color, piece+1, depth)
                    continue
                normal = CUBE[color]
                axis, sign = next((a, v) for a, v in enumerate(normal) if v)
                home = next(p for p in cells[piece] if p[axis] == sign*(cube.core_n-1))
                index = (lookup[piece, color] if cube.puzzle_kind == 'cuboid_133' else
                         lookup[transform(frame, home), transform(frame, normal)])
                color = cube.colors[index]
            for index in bits(mask):
                if output[face][index][2] is None or depth > output[face][index][2]:
                    output[face][index] = (color, piece+1, depth)
    return output


class SixViewDraft:
    def __init__(self, kind, state=None):
        self.kind = kind
        self.model = observation_model(kind)
        self.version = 2 if getattr(CuboidCube.solved(kind), 'panel_anchored', False) else 1
        self.views = [[(UNKNOWN, 0, None) for _ in range(w*h)] for w, h in self.model['shapes']]
        if state is not None:
            if state.get('kind') != kind or state.get('version') != self.version:
                raise ValueError('six.model_mismatch')
            data = state['views']
            if len(data) != 6 or any(len(data[f]) != len(self.views[f]) for f in range(6)):
                raise ValueError('six.model_mismatch')
            for face, samples in enumerate(data):
                for i, value in enumerate(samples):
                    color, group, depth = value
                    if color not in (UNKNOWN, EMPTY, PLASTIC, 0, 1, 2, 3, 4, 5):
                        raise ValueError('six.model_mismatch')
                    if not isinstance(group, int) or group < 0 or (depth is not None and depth not in self.model['levels'][face]):
                        raise ValueError('six.model_mismatch')
                    self.views[face][i] = (color, group, depth)

    @classmethod
    def from_cube(cls, cube):
        draft = cls(cube.puzzle_kind)
        draft.views = project(cube, draft.model)
        return draft

    def state(self):
        return {'version': self.version, 'kind': self.kind, 'views': [list(v) for v in self.views]}

    def rectangle(self, face, first, last):
        width, height = self.model['shapes'][face]
        r1, c1 = divmod(first, width); r2, c2 = divmod(last, width)
        return tuple(r*width+c for r in range(min(r1, r2), max(r1, r2)+1)
                     for c in range(min(c1, c2), max(c1, c2)+1))

    def paint(self, face, indices, color, depth=None):
        if color not in (UNKNOWN, EMPTY, PLASTIC, 0, 1, 2, 3, 4, 5):
            raise ValueError('six.model_mismatch')
        if depth is not None and depth not in self.model['levels'][face]:
            raise ValueError('six.model_mismatch')
        group = max((v[1] for view in self.views for v in view), default=0)+1
        for i in indices:
            self.views[face][i] = (color, group if color not in (UNKNOWN, EMPTY) else 0,
                                   depth if color not in (UNKNOWN, EMPTY) else None)

    def mark_outside(self, face):
        self.views[face] = [(EMPTY, 0, None) if c == UNKNOWN else (c, g, d) for c, g, d in self.views[face]]

    def missing(self):
        return next(((f, i) for f in FACE_ORDER for i, v in enumerate(self.views[f]) if v[0] == UNKNOWN), None)

    def match(self, seconds=6., cancel=None, node_limit=80000):
        """Bounded constraint matching. Ambiguity and exhaustion are distinct."""
        missing = self.missing()
        if missing:
            return MatchResult('incomplete', face=missing[0], cell=missing[1])
        deadline = monotonic()+seconds
        empty = tuple(sum(1 << i for i, (c, _, _) in enumerate(view) if c == EMPTY) for view in self.views)
        known_depths = [[(i, c, d) for i, (c, _, d) in enumerate(view) if d is not None] for view in self.views]
        options = []
        for placements in self.model['placements']:
            viable = []
            for p in placements:
                if any(mask & empty[f] for f, (mask, _, _) in enumerate(p.views)):
                    continue
                if any(mask & (1 << i) and (dep > d or dep == d and color != c)
                       for f, (mask, dep, color) in enumerate(p.views) for i, c, d in known_depths[f]):
                    continue
                viable.append(p)
            options.append(viable)
        if any(not p for p in options):
            return MatchResult('conflict')
        equivalence = {}; group_of = []
        for piece, placements in enumerate(options):
            signature = frozenset((p.core, p.body, p.views) for p in placements)
            group = equivalence.setdefault(signature, [])
            group.append(piece); group_of.append(group)
        patches = []
        for face, view in enumerate(self.views):
            groups = {}
            for i, (color, group, depth) in enumerate(view):
                if color >= 0:
                    groups.setdefault((color, group), []).append(i)
            for (color, group), indices in groups.items():
                mask = sum(1 << i for i in indices)
                choices = [p for opts in options for p in opts if p.views[face][2] == color and p.views[face][0] & mask == mask
                           and all(view[i][2] is None or view[i][2] == p.views[face][1] for i in indices)]
                if not choices:
                    return MatchResult('conflict', face=face, cell=indices[0])
                patches.append((face, mask, tuple(indices), choices))
        selected = {}; protected = []; solutions = {}; nodes = 0; exhausted = False
        fill_order = {}

        def limit():
            nonlocal nodes, exhausted
            nodes += 1
            if nodes > node_limit or monotonic() >= deadline or (cancel is not None and cancel.is_set()):
                exhausted = True
                return True
            return False

        def compatible(p, used_core, used_body):
            existing = selected.get(p.piece)
            if existing is not None:
                return existing is p
            if p.core & used_core or p.body & used_body:
                return False
            return all(not (p.views[f][0] & mask) or p.views[f][1] < depth
                       for f, mask, depth, owner in protected if owner != p.piece)

        def canonical(p):
            return p.piece in selected or p.piece == next(q for q in group_of[p.piece] if q not in selected)

        def visible_patch(p, patch):
            face, mask, indices, _ = patch
            depth = p.views[face][1]
            if any(q.piece != p.piece and q.views[face][0] & mask and q.views[face][1] >= depth for q in selected.values()):
                return False
            # Adjacent colour regions explicitly record a physical cut.
            width, height = self.model['shapes'][face]
            view = self.views[face]
            for f, oldmask, _, owner in protected:
                if f != face or owner != p.piece:
                    continue
                for i in indices:
                    r, c = divmod(i, width)
                    neighbours = ([i-1] if c else [])+([i+1] if c+1 < width else [])+([i-width] if r else [])+([i+width] if r+1 < height else [])
                    if any(oldmask & (1 << j) and view[j][1] != view[i][1] for j in neighbours):
                        return False
            return True

        def complete():
            frames = tuple(selected[p].frame for p in range(len(options)))
            try:
                cube = _cube_from_frames(self.kind, frames)
            except ValueError:
                return
            observed = project(cube, self.model)
            if any(c != observed[f][i][0] or (d is not None and d != observed[f][i][2])
                   for f, view in enumerate(self.views) for i, (c, _, d) in enumerate(view)):
                return
            signature = tuple(sorted((p.core, p.body, p.views) for p in selected.values()))
            solutions.setdefault(signature, cube)

        def fill(used_core, used_body):
            if len(solutions) > 1 or exhausted or limit():
                return
            if len(selected) == len(options):
                complete(); return
            candidates = {}
            for piece, opts in enumerate(options):
                if piece not in selected:
                    candidates[piece] = [p for p in opts if compatible(p, used_core, used_body)]
            piece = min(candidates, key=lambda p: len(candidates[p]))
            for p in candidates[piece]:
                group = group_of[piece][0]
                signature = (p.core, p.body, p.views)
                previous = fill_order.get(group)
                if previous is not None and signature <= previous:
                    continue
                fill_order[group] = signature
                selected[piece] = p
                fill(used_core | p.core, used_body | p.body)
                selected.pop(piece)
                if previous is None:
                    fill_order.pop(group)
                else:
                    fill_order[group] = previous
                if len(solutions) > 1 or exhausted:
                    return

        def assign(todo, used_core, used_body):
            if len(solutions) > 1 or exhausted or limit():
                return
            if not todo:
                fill(used_core, used_body); return
            choices = {i: [p for p in patches[i][3] if canonical(p) and compatible(p, used_core, used_body) and visible_patch(p, patches[i])]
                       for i in todo}
            index = min(todo, key=lambda i: len(choices[i]))
            face, mask, indices, _ = patches[index]
            for p in choices[index]:
                existed = p.piece in selected
                selected[p.piece] = p
                protected.append((face, mask, p.views[face][1], p.piece))
                assign([i for i in todo if i != index], used_core | p.core, used_body | p.body)
                protected.pop()
                if not existed:
                    selected.pop(p.piece)
                if len(solutions) > 1 or exhausted:
                    return
        assign(list(range(len(patches))), 0, 0)
        if cancel is not None and cancel.is_set():
            return MatchResult('cancelled', nodes=nodes)
        if len(solutions) > 1:
            a, b = tuple(solutions.values())[:2]
            pa, pb = project(a, self.model), project(b, self.model)
            hint = next(((f, i) for f in FACE_ORDER for i in range(len(pa[f])) if pa[f][i][2] != pb[f][i][2]), (FACE_ORDER[0], 0))
            return MatchResult('ambiguous', face=hint[0], cell=hint[1], nodes=nodes)
        if exhausted:
            return MatchResult('budget', nodes=nodes)
        return MatchResult('ok', cube=next(iter(solutions.values())), nodes=nodes) if solutions else MatchResult('conflict', nodes=nodes)


def _cube_from_frames(kind, frames):
    cells, boxes, entries, lookup, base = layout(kind)
    if getattr(CuboidCube.solved(kind), 'panel_anchored', False):
        result = CuboidCube(kind, [s.face for s in base.stickers], frames)
        result.geometry
        return result
    n = CuboidCube.solved(kind).core_n
    colors = [UNKNOWN]*len(entries)
    for piece, frame in enumerate(frames):
        for face, normal in enumerate(CUBE):
            axis, sign = next((a, v) for a, v in enumerate(normal) if v)
            for home in cells[piece]:
                if home[axis] == sign*(n-1):
                    index = lookup[piece, face] if kind == 'cuboid_133' else lookup[transform(frame, home), transform(frame, normal)]
                    colors[index] = face
    result = CuboidCube(kind, colors, frames)
    result.geometry
    return result
