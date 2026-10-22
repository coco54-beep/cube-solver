"""Generate core-preserving extension macros and compact phase tables offline."""
import argparse
import json
from pathlib import Path
import sys
import zlib
import random

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cube.cuboid import CuboidCube, layout, transform, turn_frame, IDENTITY
from cube.extended_cuboid import CORE_DIMENSIONS
from cube.polyhedral import CUBE, Move
from solver.polyhedral import inverse_word, simplify


def core_solved(cube):
    cells = layout(cube.puzzle_kind)[0]; dims = cube.core_dimensions
    return all(transform(cube.frames[i], normal) == normal
               for i, group in enumerate(cells[:cube.core_count]) for normal in CUBE
               for a, sign in (next((a, v) for a, v in enumerate(normal) if v),)
               if group[0][a] == sign*(dims[a]-1))


def visible_core_solved(cube):
    return all(cube.colors[i] == s.face for i, s in enumerate(cube.geometry.stickers)
               if s.piece < cube.core_count)


def generate(kind, depth=1, residuals=0):
    start = CuboidCube.solved(kind); cells, _, entries, lookup, base = layout(kind)
    panels = tuple((s.piece, s.face) for s in base.stickers if s.piece >= start.core_count)
    destinations = {(entries[lookup[p, f]][0], CUBE[f]): i for i, (p, f) in enumerate(panels)}
    identity = tuple(range(len(panels))); macros = {}
    # Core turns are available in every shape. Enumerate short setups, and
    # retain a conjugate only if its complete replay restores the core.
    atoms = [Move(a, layer, amount) for a in range(6)
             for layer in range(1, start.core_dimensions[next(i for i, v in enumerate(CUBE[a]) if v)])
             for amount in range(start.geometry.spec.step(a), 4, start.geometry.spec.step(a))]
    frontier = [(start, ())]
    for level in range(depth+1):
        following = []
        for setup, prefix in frontier:
            for a in range(6):
                atom = Move(a, 0, setup.geometry.spec.step(a))
                if not setup.can_apply(atom):
                    continue
                end = setup.clone().apply_move(atom)
                try:
                    end.apply_moves(inverse_word(prefix, 4))
                    if not core_solved(end):
                        continue
                    perm = tuple(destinations[transform(end.frames[p], entries[lookup[p, f]][0]),
                                              transform(end.frames[p], CUBE[f])] for p, f in panels)
                except (ValueError, KeyError):
                    continue
                word = simplify(prefix+(atom,)+inverse_word(prefix, 4), 4)
                if perm != identity and (perm not in macros or len(word) < len(macros[perm])):
                    macros[perm] = word
            if level < depth:
                for atom in atoms:
                    if prefix and atom.axis == prefix[-1].axis:
                        continue
                    following.append((setup.clone().apply_move(atom), prefix+(atom,)))
        frontier = following
        print(kind, 'setups depth', level, 'macros', len(macros), flush=True)
    for seed in range(residuals):
        from solver.cuboid_extended import _core_cube, _tokens, _align_centres, _canonical_alignment, _solve_small_core, _solve_rectangular_core
        end = start.clone(); rng = random.Random(7751+seed); word = []
        for _ in range(18):
            atom = rng.choice(end.moves())
            atom = Move(atom.axis, atom.layer, atom.amount*rng.randrange(1, end.geometry.spec.order(atom.axis)) % 4)
            end.apply_move(atom); word.append(atom)
        if kind == 'cuboid_234':
            word.extend(_solve_rectangular_core(end, None))
        else:
            word.extend(_align_centres(end)); core = _core_cube(end)
            if core.n == 4:
                from solver.solver4 import solve_4x4
                solution = solve_4x4(core)
            else:
                solution = _solve_small_core(core)
            if not solution.success:
                continue
            moves = _tokens(end, solution.moves); end.apply_moves(moves); word.extend(moves)
            alignment = _canonical_alignment(end)
            if alignment is None:
                continue
            end.apply_moves(alignment); word.extend(alignment)
        if not core_solved(end):
            raise ValueError('Core residual did not replay')
        perm = tuple(destinations[transform(end.frames[p], entries[lookup[p, f]][0]),
                                  transform(end.frames[p], CUBE[f])] for p, f in panels)
        word = tuple(word)
        if perm != identity and (perm not in macros or len(word) < len(macros[perm])):
            macros[perm] = word
        print(kind, 'residual', seed, 'macros', len(macros), flush=True)
    # A core wing with one visible side colour has an unmarked U/D side.
    # Its equivalent partner must remain interchangeable. Generate legal
    # words for these invisible swaps, rather than imposing extra colours.
    if kind in ('cuboid_234', 'cuboid_335', 'cuboid_446'):
        from solver.cuboid_extended import _core_cube, _tokens, _solve_rectangular_core, _solve_small_core, whole_core
        from cube.appearance import ROTATIONS
        from cube.colors import DEFAULT_COLORS
        from collections import deque
        core_at = {g[0]: p for p, g in enumerate(cells[:start.core_count])}
        core_faces = {p: [s.face for s in base.stickers if s.piece == p] for p in core_at.values()}
        pairs = []
        for p, faces in core_faces.items():
            if len(faces) != 1:
                continue
            f = turn_frame(faces[0], 2); q = core_at.get(transform(f, cells[p][0]))
            if q is not None and p < q and core_faces[q] == faces:
                pairs.append((p, q, f))
        choices = [(pair,) for pair in pairs] if kind in ('cuboid_446', 'cuboid_234') else [tuple(pairs[:2])]
        for number, choice in enumerate(choices):
            goal = start.clone(); frames = list(goal.frames)
            for p, q, f in choice:
                frames[p] = frames[q] = f
            goal.frames = tuple(frames)
            if kind == 'cuboid_234':
                # The helper only reads core frames. Keep the temporary
                # extension geometry out of the target construction.
                from cube.cuboid_observation import _cube_from_frames
                from solver.cuboid_static import solve_fixed_cuboid
                from cube.cuboid import multiply
                rot = turn_frame(1, 3); undo = turn_frame(1, 1)
                target, boxes, *_ = layout('cuboid_223')
                at = {tuple(lo+hi for lo, hi in b): i for i, b in enumerate(boxes)}
                target_frames = [None]*len(target)
                for p, g in enumerate(cells[:start.core_count]):
                    target_frames[at[transform(rot, g[0])]] = multiply(multiply(rot, goal.frames[p]), undo)
                helper = _cube_from_frames('cuboid_223', target_frames)
                forward = []
                for m in solve_fixed_cuboid(helper):
                    a = next(a for a, v in enumerate(CUBE[m.axis]) if v)
                    width = len({helper.geometry.centres[p][a] for p in helper.geometry.layers[m.axis][m.layer]})
                    forward.append(Move(CUBE.index(transform(undo, CUBE[m.axis])), width, m.amount))
            else:
                helper = _core_cube(goal)
                if helper.n == 4:
                    from solver.solver4 import solve_4x4
                    solution = solve_4x4(helper)
                else:
                    solution = _solve_small_core(helper)
                if not solution.success:
                    raise ValueError(solution.message)
                forward = list(_tokens(start, solution.moves)); helper.apply_moves(solution.moves)
                targets = {DEFAULT_COLORS[f]: n for f, n in zip(('U','R','F','D','L','B'), CUBE)}
                normals = {(normal, targets[c]) for piece in helper.cubies.values() for normal, c in piece.stickers.items()}
                todo = deque([(IDENTITY, ())]); seen = {IDENTITY}
                from cube.cuboid import multiply
                while todo:
                    f, w = todo.popleft()
                    if all(transform(f, a) == b for a, b in normals):
                        forward.extend(w); break
                    for a in range(3):
                        nxt = multiply(turn_frame(a, 1), f)
                        if nxt not in seen:
                            seen.add(nxt); todo.append((nxt, w+whole_core(start, a, 1)))
            word = inverse_word(forward, 4); end = start.clone().apply_moves(word)
            if not visible_core_solved(end):
                raise ValueError('Invisible core swap changed visible colours')
            perm = tuple(destinations[transform(end.frames[p], entries[lookup[p, f]][0]),
                                      transform(end.frames[p], CUBE[f])] for p, f in panels)
            if perm != identity and (perm not in macros or len(word) < len(macros[perm])):
                macros[perm] = word
            print(kind, 'equivalent core', number, 'macros', len(macros), flush=True)
    records = [{'permutation': perm, 'word': [[m.axis, m.layer, m.amount] for m in word]}
               for perm, word in sorted(macros.items(), key=lambda item: len(item[1]))]
    payload = json.dumps({'kind': kind, 'panels': panels, 'records': records}, separators=(',', ':')).encode()
    destination = Path(__file__).resolve().parents[1]/'solver'/'data'/f'{kind}_extensions.bin'
    destination.write_bytes(b'CE01'+zlib.compress(payload, 9))
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('kinds', nargs='*', default=list(CORE_DIMENSIONS))
    parser.add_argument('--depth', type=int, default=1)
    parser.add_argument('--residuals', type=int, default=0)
    args = parser.parse_args()
    for kind in args.kinds:
        generate(kind, args.depth, args.residuals)
        from solver.cuboid_static import write_phase_tables
        destination = Path(__file__).resolve().parents[1]/'solver'/'data'/f'{kind}_phases.bin'
        write_phase_tables(kind, destination, lambda *a: print(kind, 'phase', *a, flush=True))
        print(destination, destination.stat().st_size, flush=True)
