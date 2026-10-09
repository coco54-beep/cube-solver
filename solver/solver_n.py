"""State-based higher order solver using independent piece orbits.

The 3×3 core is solved first. Each wing orbit is then sorted with slice
commutators, and independent center orbits are sorted last. Solutions are
replayed on the original input before being returned to the UI.
"""
import time

from cube.colors import DEFAULT_COLORS
from cube.coordinates import get_d_maxc, FACE_NORMALS, FACE_AXIS_SIGN, coord_values, layer_values
from cube.cubie_model import Cubie
from cube.cube3 import Cube3
from cube.conversion import cubies_to_facelets
from solver.result import SolveResult, SolveStage
from solver import nxn_orbits as orbit


def canonical_cube(cube):
    work = cube.clone()
    if cube.n % 2:
        _, m = get_d_maxc(cube.n)
        mapping = {}
        for face, normal in FACE_NORMALS.items():
            pos = tuple(v * m for v in normal)
            color = work.cubies[pos].stickers.get(normal)
            if color is None or color in mapping:
                raise ValueError("nxn.error.fixed")
            mapping[color] = DEFAULT_COLORS[face]
        if set(mapping) != set(DEFAULT_COLORS.values()):
            raise ValueError("nxn.error.fixed")
        for cb in work.cubies.values():
            cb.stickers = {normal: mapping[color] for normal, color in cb.stickers.items()}
    return work


def core_facelets(cube):
    from solver.solver3 import _tface, _tcubie, _build_cubestring
    core = Cube3.solved()
    _, m = get_d_maxc(cube.n)
    for pos, cb in cube.cubies.items():
        if len(cb.stickers) == 3 or (cube.n % 2 and len(cb.stickers) == 2 and 0 in pos):
            small = tuple(0 if v == 0 else (1 if v > 0 else -1) for v in pos)
            core.cubies[small] = Cubie(small, small, dict(cb.stickers))
    faces = cubies_to_facelets(core.cubies, 3)
    fc = _tface.FaceCube()
    code = fc.from_string(_build_cubestring(faces))
    if code != _tcubie.CUBE_OK:
        raise ValueError("nxn.error.core")
    cc = fc.to_cubie_cube()
    if not cube.n % 2 and cc.corner_parity():
        # On even cubes the virtual middle edges are synthetic. Give them the
        # corner permutation's parity to form a legal 3×3 search problem.
        cc.ep[0], cc.ep[1] = cc.ep[1], cc.ep[0]
    if cc.verify() != _tcubie.CUBE_OK:
        raise ValueError("nxn.error.core")
    string = cc.to_facelet_cube().to_string()
    return {face: [[DEFAULT_COLORS[string[k * 9 + r * 3 + c]] for c in range(3)]
                   for r in range(3)] for k, face in enumerate(("U", "R", "F", "D", "L", "B"))}


def inspect_state(cube):
    """Validate visible piece identities, center color orbits, and the core."""
    work = canonical_cube(cube)
    core_facelets(work)
    wings = [ps for ps in orbit.orbits(work.n, 2) if len(ps) == 24]
    centers = [ps for ps in orbit.orbits(work.n, 1) if len(ps) == 24]
    for ps in wings:
        orbit.wing_permutation(work, ps)
    for ps in centers:
        orbit.center_permutation(work, ps)
    return work, wings, centers


def _compress(moves, n):
    from cube.notation import parse_move_full
    result = []
    block_axis = None
    block = []
    values = sorted(coord_values(n), reverse=True)
    value_index = {value: i for i, value in enumerate(values)}

    def flush():
        nonlocal block_axis, block
        if not block:
            return
        turns = [0] * n
        for face, layers, count in block:
            _, sign = FACE_AXIS_SIGN[face]
            for value in layer_values(n, face, layers=layers):
                index = value_index[value]
                turns[index] = (turns[index] + sign * count) % 4

        # Same-axis layers commute. Encode the per-slice turn vector from both
        # outer faces and keep whichever direction needs fewer visible turns.
        face = {0: "R", 1: "U", 2: "F"}[block_axis]
        opposite = {0: "L", 1: "D", 2: "B"}[block_axis]
        alternatives = []

        prefix_ops = {}
        for width in range(1, n):
            count = (turns[width - 1] - turns[width]) % 4
            if count:
                prefix_ops[(face, width)] = count
        whole = turns[-1]
        if whole:
            key = (face, n - 1)
            prefix_ops[key] = (prefix_ops.get(key, 0) + whole) % 4
            prefix_ops[(opposite, 1)] = (-whole) % 4
        alternatives.append(prefix_ops)

        suffix_ops = {}
        for width in range(1, n):
            count = (turns[n - width] - turns[n - width - 1]) % 4
            if count:
                suffix_ops[(opposite, width)] = (-count) % 4
        whole = turns[0]
        if whole:
            key = (opposite, n - 1)
            suffix_ops[key] = (suffix_ops.get(key, 0) - whole) % 4
            suffix_ops[(face, 1)] = whole
        alternatives.append(suffix_ops)

        encoded = []
        for ops in alternatives:
            tokens = []
            for (label, width), count in sorted(ops.items()):
                if count:
                    prefix = str(width) if width > 1 else ""
                    suffix = {1: "", 2: "2", 3: "'"}[count]
                    tokens.append(prefix + label + suffix)
            encoded.append(tokens)
        compact = min(encoded, key=len)
        if len(compact) < len(block):
            result.extend(compact)
        else:
            result.extend((str(width) if width > 1 else "") + face
                          + {1: "", 2: "2", 3: "'"}[count]
                          for face, width, count in block)
        block_axis, block = None, []

    for move in moves:
        face, layers, count = parse_move_full(move)
        if face not in FACE_AXIS_SIGN:
            flush()
            result.append(move)
            continue
        axis = FACE_AXIS_SIGN[face][0]
        if block_axis is not None and axis != block_axis:
            flush()
        block_axis = axis
        block.append((face, layers, count))
    flush()
    return result


def solve_nxn(cube, cancel_event=None, progress_callback=None):
    started = time.perf_counter()
    all_moves, stages = [], []

    def cancel():
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("nxn.cancelled")

    def emit(key, progress, **values):
        from app.i18n import tr
        if progress_callback:
            progress_callback({"stage": "nxn", "progress": progress,
                               "label": tr(key, **values)})

    def apply(atoms):
        moves = _compress(orbit.expand(atoms, work.n), work.n)
        for move in moves:
            cancel()
            work.apply_move(move)
        all_moves.extend(moves)
        return moves

    try:
        cancel()
        emit("nxn.solving.inspect", .02)
        work, wings, centers = inspect_state(cube)
        emit("nxn.solving.core", .05)
        from solver.solver3 import solve_3x3
        core = solve_3x3(core_facelets(work))
        if not core.success:
            raise ValueError("nxn.error.core")
        for move in core.moves:
            cancel()
            work.apply_move(move)
        all_moves.extend(core.moves)
        stages.append(SolveStage("nxn_core", "nxn.solving.core", core.moves))
        for k, positions in enumerate(wings):
            cancel()
            emit("nxn.solving.wings", .12 + .38 * k / max(1, len(wings)),
                 i=k + 1, total=len(wings))
            before = len(all_moves)
            perm = orbit.wing_permutation(work, positions)
            if orbit.parity(perm):
                _, m = get_d_maxc(work.n)
                offset = next(abs(v) for v in positions[0] if abs(v) < m)
                apply([("R", offset, 1)])
                perm = orbit.wing_permutation(work, positions)
            targets = orbit.three_cycles(perm)
            if targets:
                base, start = orbit.primitive(work.n, positions, True, cancel)
                for atoms in orbit.conjugates(work.n, positions, base, start, targets, cancel):
                    apply(atoms)
            if orbit.wing_permutation(work, positions) != list(range(len(positions))):
                raise RuntimeError("nxn.error.replay")
            stages.append(SolveStage("nxn_wings", "nxn.solving.wings", all_moves[before:]))
        for k, positions in enumerate(centers):
            cancel()
            emit("nxn.solving.centers", .5 + .46 * k / max(1, len(centers)),
                 i=k + 1, total=len(centers))
            before = len(all_moves)
            targets = orbit.three_cycles(orbit.center_permutation(work, positions))
            if targets:
                base, start = orbit.primitive(work.n, positions, False, cancel)
                for atoms in orbit.conjugates(work.n, positions, base, start, targets, cancel):
                    apply(atoms)
            stages.append(SolveStage("nxn_centers", "nxn.solving.centers", all_moves[before:]))
        emit("nxn.solving.replay", .98)
        moves = _compress(all_moves, work.n)
        replay = cube.clone()
        for move in moves:
            cancel()
            replay.apply_move(move)
        if not work.is_solved() or not replay.is_solved():
            raise RuntimeError("nxn.error.replay")
        emit("nxn.solving.done", 1)
        return SolveResult(True, moves, "", int((time.perf_counter() - started) * 1000),
                           len(moves), stages)
    except Exception as exc:
        from app.i18n import tr
        key = str(exc)
        message = tr(key) if key.startswith("nxn.") else key
        return SolveResult(False, [], message, int((time.perf_counter() - started) * 1000), 0, [])
