"""Restore the internal core, then the independently movable extensions.

All state reconstruction uses physical piece frames and colours. A returned
word is accepted only after legal replay on the original entered model.
"""
from collections import defaultdict, deque
from itertools import product

from cube.cuboid import CuboidCube, FACES, IDENTITY, layout, transform, multiply, turn_frame
from cube.polyhedral import CUBE, Move
from solver.polyhedral import simplify, compose


def whole_core(cube, axis, amount):
    a = next(a for a, v in enumerate(CUBE[axis]) if v)
    return (Move(axis, cube.core_dimensions[a]-1, amount), Move(axis+3, 1, -amount % 4))


def _core_cube(cube):
    from cube.cubie_model import Cubie
    from cube.colors import DEFAULT_COLORS
    from cube.cube2 import Cube2
    from cube.cube3 import Cube3
    from cube.cube4 import Cube4
    n = cube.core_dimensions[0]
    if cube.core_dimensions != (n, n, n):
        raise ValueError('Expected a cubic core')
    scale = 2 if n == 3 else 1
    cells = layout(cube.puzzle_kind)[0]
    pieces = {}
    for i, group in enumerate(cells[:cube.core_count]):
        home = group[0]; frame = cube.frames[i]
        stickers = {transform(frame, normal): DEFAULT_COLORS[FACES[face]]
                    for face, normal in enumerate(CUBE)
                    for a, sign in (next((a, v) for a, v in enumerate(normal) if v),)
                    if home[a] == sign*(n-1)}
        if stickers:
            pos = tuple(v//scale for v in transform(frame, home))
            pieces[pos] = Cubie(tuple(v//scale for v in home), pos, stickers)
    return {2: Cube2, 3: Cube3, 4: Cube4}[n](pieces)


def _canonical_alignment(cube):
    """Return whole-core turns making uniform core faces canonical."""
    from cube.colors import DEFAULT_COLORS
    target = {DEFAULT_COLORS[f]: normal for f, normal in zip(FACES, CUBE)}
    core = _core_cube(cube)
    pairs = {(normal, target[c]) for piece in core.cubies.values() for normal, c in piece.stickers.items()}
    todo = deque([(IDENTITY, ())]); seen = {IDENTITY}
    while todo:
        frame, word = todo.popleft()
        if all(transform(frame, a) == b for a, b in pairs):
            return word
        for axis in range(3):
            nxt = multiply(turn_frame(axis, 1), frame)
            if nxt not in seen:
                seen.add(nxt); todo.append((nxt, word+whole_core(cube, axis, 1)))
    return None


def _align_centres(cube):
    if cube.core_dimensions != (3, 3, 3):
        return ()
    cells = layout(cube.puzzle_kind)[0]
    pairs = [(transform(cube.frames[i], g[0]), g[0]) for i, g in enumerate(cells[:cube.core_count])
             if sum(v != 0 for v in g[0]) == 1]
    todo = deque([(IDENTITY, ())]); seen = {IDENTITY}
    while todo:
        f, word = todo.popleft()
        if all(transform(f, a) == b for a, b in pairs):
            cube.apply_moves(word); return word
        for a in range(3):
            nxt = multiply(turn_frame(a, 1), f)
            if nxt not in seen:
                seen.add(nxt); todo.append((nxt, word+whole_core(cube, a, 1)))
    raise ValueError('cuboid.identity_unreachable')


def _tokens(cube, tokens):
    from cube.notation import parse_move_full
    result = []
    for compound in tokens:
        for token in compound.split():
            face, width, count = parse_move_full(token)
            if face in ('x', 'y', 'z'):
                result.extend(whole_core(cube, {'x': 1, 'y': 0, 'z': 2}[face], -count % 4))
            else:
                result.append(Move(FACES.index(face), width, -count % 4))
    return tuple(result)


def _solve_small_core(core):
    """Embed two-order corners in a legal 3x3; avoid the RAM-heavy 2x2 BFS."""
    from cube.cube3 import Cube3
    from cube.conversion import cubies_to_facelets
    from solver.solver3 import solve_3x3, verify_3x3
    if core.n == 2:
        full = Cube3.solved()
        for pos, piece in core.cubies.items():
            full.cubies[pos] = piece.clone()
        facelets = cubies_to_facelets(full.cubies, 3)
        ok, _ = verify_3x3(facelets)
        if not ok:
            # Match corner parity with a single edge transposition. Both
            # artificial edges keep their U sticker on U (no edge flip).
            a, b = full.cubies[(1, 1, 0)], full.cubies[(0, 1, 1)]
            a.stickers[(1, 0, 0)], b.stickers[(0, 0, 1)] = b.stickers[(0, 0, 1)], a.stickers[(1, 0, 0)]
            facelets = cubies_to_facelets(full.cubies, 3)
    else:
        facelets = cubies_to_facelets(core.cubies, 3)
    return solve_3x3(facelets, timeout=10.)


def _legal_three_core(cube):
    """The unmarked U/D side of a one-colour core edge is interchangeable."""
    from cube.conversion import cubies_to_facelets
    from solver.solver3 import verify_3x3
    if cube.core_dimensions != (3, 3, 3):
        return
    cells, _, _, lookup, base = layout(cube.puzzle_kind)
    home_at = {g[0]: p for p, g in enumerate(cells[:cube.core_count])}
    pairs = []
    for p in range(cube.core_count):
        faces = [s.face for s in base.stickers if s.piece == p]
        if len(faces) != 1 or sum(v != 0 for v in cells[p][0]) != 2:
            continue
        rotation = turn_frame(faces[0], 2); q = home_at.get(transform(rotation, cells[p][0]))
        if q is not None and p < q:
            pairs.append((p, q, rotation))
    original = cube.frames
    for mask in range(1 << len(pairs)):
        frames = list(original)
        for bit, (p, q, rotation) in enumerate(pairs):
            if mask & (1 << bit):
                frames[p] = multiply(original[q], rotation)
                frames[q] = multiply(original[p], rotation)
        cube.frames = tuple(frames); cube._geometry_cache = None
        if verify_3x3(cubies_to_facelets(_core_cube(cube).cubies, 3))[0]:
            return
    cube.frames = original; cube._geometry_cache = None
    raise ValueError('cuboid.identity_unreachable')


def _solve_rectangular_core(cube, cancel):
    """Rotate the internal 2x2x3 into the fixed Tower solver's coordinates."""
    from cube.cuboid_observation import _cube_from_frames
    from solver.cuboid_static import solve_fixed_cuboid
    rotation = turn_frame(1, 3); undo = turn_frame(1, 1)
    source = layout(cube.puzzle_kind)[0]
    target, boxes, *_ = layout('cuboid_223')
    home_at = {tuple((lo+hi) for lo, hi in box): i for i, box in enumerate(boxes)}
    frames = [None]*len(target)
    for i, group in enumerate(source[:cube.core_count]):
        home = transform(rotation, group[0])
        frames[home_at[home]] = multiply(multiply(rotation, cube.frames[i]), undo)
    helper = _cube_from_frames('cuboid_223', frames)
    result = []
    for move in solve_fixed_cuboid(helper, cancel):
        axis = CUBE.index(transform(undo, CUBE[move.axis]))
        a = next(a for a, v in enumerate(CUBE[move.axis]) if v)
        width = len({helper.geometry.centres[p][a] for p in helper.geometry.layers[move.axis][move.layer]})
        result.append(Move(axis, width, move.amount))
    cube.apply_moves(result)
    return tuple(result)


def _extension_state(cube):
    from solver.cuboid_extensions import extension_mechanism
    adapter, panels, _, _ = extension_mechanism(cube.puzzle_kind)
    cells, boxes, entries, lookup, base = layout(cube.puzzle_kind)
    position_at = {(entries[lookup[p, f]][0], CUBE[f]): i for i, (p, f) in enumerate(panels)}
    by_piece = defaultdict(list)
    for i, (p, f) in enumerate(panels):
        by_piece[p].append((i, f))
    orbit_at = {p: phase for phase in adapter.phase_points for i in phase for p, _ in (panels[i],)}
    identities = {}
    for p, points in by_piece.items():
        identities[orbit_at[p], tuple(sorted(f for i, f in points))] = p
    result = [None]*len(panels)
    for p, points in by_piece.items():
        frame = cube.frames[p]
        destinations = [(position_at[transform(frame, entries[lookup[p, f]][0]), transform(frame, CUBE[f])],
                         cube.colors[lookup[p, f]]) for i, f in points]
        physical_piece = panels[destinations[0][0]][0]
        home = identities[orbit_at[physical_piece], tuple(sorted(c for i, c in destinations))]
        sources = {f: i for i, f in by_piece[home]}
        for dest, color in destinations:
            result[sources[color]] = dest
    if any(i is None for i in result) or len(set(result)) != len(result):
        raise ValueError('cuboid.identity_unreachable')
    return tuple(result)


def solve_extended_cuboid(original, cancel=None, progress=None):
    from solver.cuboid_static import normalize, phase_tables, mechanism
    from solver.cuboid_extensions import expand
    cube = normalize(original, cancel).clone(); cube.history = None
    def check():
        if cancel and cancel():
            raise InterruptedError()
    check(); word = []
    if cube.puzzle_kind == 'cuboid_234':
        word.extend(_solve_rectangular_core(cube, cancel))
    else:
        word.extend(_align_centres(cube)); check(); _legal_three_core(cube)
        core = _core_cube(cube)
        if core.n <= 3:
            result = _solve_small_core(core)
        else:
            from solver.solver4 import solve_4x4
            class Cancel:
                def is_set(self):
                    return bool(cancel and cancel())
            result = solve_4x4(core, cancel_event=Cancel())
        check()
        if not result.success:
            raise ValueError(result.message)
        moves = _tokens(cube, result.moves); cube.apply_moves(moves); word.extend(moves)
        alignment = _canonical_alignment(cube)
        if alignment is None:
            raise ValueError('cuboid.core_replay_failed')
        cube.apply_moves(alignment); word.extend(alignment)
    check()
    if progress:
        progress(1, 2)
    current = _extension_state(cube)
    g = mechanism(cube.puzzle_kind)[0].geometry
    for table in phase_tables(cube.puzzle_kind):
        check(); local = {p: i for i, p in enumerate(table.points)}
        try:
            projected = bytes(local[current[p]] for p in table.points)
        except KeyError as error:
            raise ValueError('cuboid.identity_unreachable') from error
        actions = table.solve(projected)
        if actions is None:
            raise ValueError('cuboid.identity_unreachable')
        for action in actions:
            current = compose(current, g.permutation(action))
        word.extend(expand(cube.puzzle_kind, actions))
    # Do not reorder a shape-dependent outer turn past another band.
    replay = original.entered()
    for move in word:
        check(); replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError('cuboid.replay_failed')
    if progress:
        progress(1, 1)
    return tuple(word)
